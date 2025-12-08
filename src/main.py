import os
import json
import enum
from datetime import date
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel

# =============================================================================
# 1. DATABASE SETUP
# =============================================================================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./football.db")

# Fix for Render's Postgres URL format
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =============================================================================
# 2. DATABASE MODELS (TABLES)
# =============================================================================

class MatchResult(str, enum.Enum):
    TEAM_A = "TEAM_A"
    TEAM_B = "TEAM_B"
    DRAW = "DRAW"

class MatchPlayer(Base):
    __tablename__ = "match_players"
    match_id = Column(Integer, ForeignKey("matches.id"), primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), primary_key=True)
    team = Column(String, nullable=False)

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    balance = Column(Float, default=0.0)
    matches = relationship("Match", secondary="match_players", back_populates="players")

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    result = Column(String, nullable=False)
    is_double_points = Column(Boolean, default=False)
    players = relationship("Player", secondary="match_players", back_populates="matches")

class Champion(Base):
    __tablename__ = "champions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    titles = Column(Integer, default=1)

class SeasonArchive(Base):
    __tablename__ = "season_archive"
    id = Column(Integer, primary_key=True, index=True)
    season_name = Column(String)
    data_json = Column(Text) # Stores the full table snapshot
    date = Column(Date)

# Create tables
Base.metadata.create_all(bind=engine)

# =============================================================================
# 3. PYDANTIC SCHEMAS (DATA VALIDATION)
# =============================================================================

class PlayerCreate(BaseModel):
    name: str

class PaymentSchema(BaseModel):
    player_id: int
    amount: float

class PlayerSchema(BaseModel):
    id: int
    name: str
    balance: float
    is_active: bool
    class Config:
        from_attributes = True

class MatchCreate(BaseModel):
    date: date
    result: MatchResult
    team_a_players: List[int]
    team_b_players: List[int]
    is_double_points: bool = False

class ChampionSchema(BaseModel):
    name: str
    titles: int
    class Config:
        from_attributes = True

class CloseSeasonSchema(BaseModel):
    champion_name: str
    season_name: str

class ArchiveSchema(BaseModel):
    id: int
    season_name: str
    date: date
    data_json: str
    class Config:
        from_attributes = True

# =============================================================================
# 4. API LOGIC
# =============================================================================

app = FastAPI(title="Terças FC API V3")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- HELPER LOGIC ---
def calculate_table_stats(db: Session):
    players = db.query(Player).filter(Player.is_active == True).all()
    matches = db.query(Match).all()

    # Initialize stats
    stats = {p.id: {"id": p.id, "name": p.name, "games_played": 0, "wins": 0, "draws": 0, "losses": 0, "points": 0} for p in players}

    for m in matches:
        multiplier = 2 if m.is_double_points else 1
        links = db.query(MatchPlayer).filter(MatchPlayer.match_id == m.id).all()

        for link in links:
            pid = link.player_id
            if pid not in stats: continue

            stats[pid]["games_played"] += 1

            if m.result == "DRAW":
                stats[pid]["draws"] += 1
                stats[pid]["points"] += (2 * multiplier)
            elif (m.result == "TEAM_A" and link.team == "A") or (m.result == "TEAM_B" and link.team == "B"):
                stats[pid]["wins"] += 1
                stats[pid]["points"] += (3 * multiplier)
            else:
                stats[pid]["losses"] += 1
                stats[pid]["points"] += (1 * multiplier)

    # Sort by Points, then Games Played
    res = list(stats.values())
    res.sort(key=lambda x: (x["points"], x["games_played"]), reverse=True)
    return res

# --- ENDPOINTS ---

@app.get("/table/")
def get_table(db: Session = Depends(get_db)):
    return calculate_table_stats(db)

@app.post("/players/", response_model=PlayerSchema)
def create_player(player: PlayerCreate, db: Session = Depends(get_db)):
    if db.query(Player).filter(Player.name == player.name).first():
        raise HTTPException(400, "Player already exists")
    new_player = Player(name=player.name, balance=0.0, is_active=True)
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    return new_player

@app.get("/players/", response_model=List[PlayerSchema])
def read_players(db: Session = Depends(get_db)):
    return db.query(Player).filter(Player.is_active == True).all()

@app.get("/players/all", response_model=List[PlayerSchema])
def read_all_players(db: Session = Depends(get_db)):
    return db.query(Player).all()

@app.post("/players/pay")
def register_payment(payment: PaymentSchema, db: Session = Depends(get_db)):
    p = db.query(Player).filter(Player.id == payment.player_id).first()
    if not p:
        raise HTTPException(404, "Player not found")
    p.balance += payment.amount
    db.commit()
    return {"message": "Payment recorded"}

@app.post("/matches/")
def create_match(match: MatchCreate, db: Session = Depends(get_db)):
    # 1. Create Match
    db_match = Match(date=match.date, result=match.result, is_double_points=match.is_double_points)
    db.add(db_match)
    db.commit()
    db.refresh(db_match)

    # 2. Add Players & Charge Cost
    GAME_COST = 3.0
    all_pids = match.team_a_players + match.team_b_players

    for pid in all_pids:
        team = "A" if pid in match.team_a_players else "B"
        db.add(MatchPlayer(match_id=db_match.id, player_id=pid, team=team))

        # Charge balance
        p = db.query(Player).filter(Player.id == pid).first()
        if p:
            p.balance -= GAME_COST

    db.commit()
    return {"message": "Match created and balances updated"}

# -- CHAMPIONS & HISTORY ENDPOINTS --

@app.get("/champions/", response_model=List[ChampionSchema])
def get_champions(db: Session = Depends(get_db)):
    return db.query(Champion).order_by(Champion.titles.desc()).all()

@app.post("/champions/remove")
def remove_champion_title(data: PlayerCreate, db: Session = Depends(get_db)):
    """Removes 1 title from a champion. If titles=0, removes from list."""
    champ = db.query(Champion).filter(Champion.name == data.name).first()
    if not champ:
        raise HTTPException(404, "Champion not found")

    if champ.titles > 1:
        champ.titles -= 1
    else:
        db.delete(champ)

    db.commit()
    return {"message": f"Removed 1 title from {data.name}"}

@app.post("/season/close")
def close_season(data: CloseSeasonSchema, db: Session = Depends(get_db)):
    # 1. Update/Create Champion
    champ = db.query(Champion).filter(Champion.name == data.champion_name).first()
    if champ:
        champ.titles += 1
    else:
        db.add(Champion(name=data.champion_name, titles=1))

    # 2. Archive Current Stats
    final_stats = calculate_table_stats(db)
    archive_json = json.dumps(final_stats) # Save as JSON string

    archive = SeasonArchive(
        season_name=f"{data.season_name} ({date.today()})",
        date=date.today(),
        data_json=archive_json
    )
    db.add(archive)

    # 3. Reset Games (Start Fresh)
    db.query(MatchPlayer).delete()
    db.query(Match).delete()

    db.commit()
    return {"message": "Season closed, archived, and reset!"}

@app.get("/history/", response_model=List[ArchiveSchema])
def get_history(db: Session = Depends(get_db)):
    return db.query(SeasonArchive).order_by(SeasonArchive.date.desc()).all()

@app.delete("/reset/")
def reset_season_manual(db: Session = Depends(get_db)):
    """Manual reset without archiving (Danger Zone)"""
    db.query(MatchPlayer).delete()
    db.query(Match).delete()
    db.commit()
    return {"message": "Manual reset done"}