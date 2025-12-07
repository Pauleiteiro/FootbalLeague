from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
import enum

# --- 1. CONFIGURAÇÃO BASE DE DADOS ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./tercasfc.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2. TABELAS (MODELS) ---
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
    matches = relationship("Match", secondary="match_players", back_populates="players")

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    result = Column(String, nullable=False)
    is_double_points = Column(Boolean, default=False)
    players = relationship("Player", secondary="match_players", back_populates="matches")

# NOVA TABELA: CAMPEÕES
class Champion(Base):
    __tablename__ = "champions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    titles = Column(Integer, default=1) # Quantos troféus tem

Base.metadata.create_all(bind=engine)

# --- 3. SCHEMAS (JSON) ---
class PlayerCreate(BaseModel):
    name: str

class PlayerSchema(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

# No src/main.py
class MatchCreate(BaseModel):
    date: date
    result: MatchResult
    team_a_players: List[int]
    team_b_players: List[int]
    is_double_points: bool = False

class PlayerStandings(BaseModel):
    id: int
    name: str
    games_played: int
    wins: int
    draws: int
    losses: int
    points: int

class ChampionSchema(BaseModel):
    name: str
    titles: int
    class Config:
        from_attributes = True

# --- 4. API ENDPOINTS ---
app = FastAPI(title="Terças FC Campeonato")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -- PLAYERS & MATCHES --
@app.post("/players/", response_model=PlayerSchema)
def create_player(player: PlayerCreate, db: Session = Depends(get_db)):
    db_player = db.query(Player).filter(Player.name == player.name).first()
    if db_player:
        raise HTTPException(status_code=400, detail="Player exists")
    new_player = Player(name=player.name)
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    return new_player

@app.get("/players/", response_model=List[PlayerSchema])
def read_players(db: Session = Depends(get_db)):
    return db.query(Player).all()

# --- SUBSTITUI A FUNÇÃO create_match POR ESTA ---
@app.post("/matches/")
def create_match(match: MatchCreate, db: Session = Depends(get_db)):
    print(f"👉 A REGISTAR JOGO: {match.result} | Dobrar: {match.is_double_points}")
    print(f"   Equipa A IDs: {match.team_a_players}")
    print(f"   Equipa B IDs: {match.team_b_players}")

    # 1. Criar o Jogo
    db_match = Match(date=match.date, result=match.result, is_double_points=match.is_double_points)
    db.add(db_match)
    db.commit()
    db.refresh(db_match)

    # 2. Ligar Jogadores
    for pid in match.team_a_players:
        db.add(MatchPlayer(match_id=db_match.id, player_id=pid, team="A"))

    for pid in match.team_b_players:
        db.add(MatchPlayer(match_id=db_match.id, player_id=pid, team="B"))

    db.commit()
    print("✅ Jogo Gravado na Base de Dados!")
    return {"message": "Match recorded"}

@app.delete("/reset/")
def reset_season(db: Session = Depends(get_db)):
    db.query(MatchPlayer).delete()
    db.query(Match).delete()
    db.commit()
    return {"message": "Season reset success"}

# -- TABLE LOGIC --
@app.get("/table/", response_model=List[PlayerStandings])
def get_table(db: Session = Depends(get_db)):
    players = db.query(Player).all()
    matches = db.query(Match).all()
    stats = {p.id: {"id": p.id, "name": p.name, "games_played": 0, "wins": 0, "draws": 0, "losses": 0, "points": 0} for p in players}

    for m in matches:
        multiplier = 2 if m.is_double_points else 1
        links = db.query(MatchPlayer).filter(MatchPlayer.match_id == m.id).all()
        for link in links:
            pid = link.player_id
            if pid not in stats: continue
            stats[pid]["games_played"] += 1
            team = link.team
            if m.result == "DRAW":
                stats[pid]["draws"] += 1; stats[pid]["points"] += (2 * multiplier)
            elif m.result == "TEAM_A":
                if team == "A": stats[pid]["wins"] += 1; stats[pid]["points"] += (3 * multiplier)
                else: stats[pid]["losses"] += 1; stats[pid]["points"] += (1 * multiplier)
            elif m.result == "TEAM_B":
                if team == "B": stats[pid]["wins"] += 1; stats[pid]["points"] += (3 * multiplier)
                else: stats[pid]["losses"] += 1; stats[pid]["points"] += (1 * multiplier)

    res = list(stats.values())
    res.sort(key=lambda x: (x["points"], x["games_played"]), reverse=True)
    return res

# -- CHAMPIONS LOGIC (NOVO) --
@app.get("/champions/", response_model=List[ChampionSchema])
def get_champions(db: Session = Depends(get_db)):
    # Ordenar por titulos (quem tem mais aparece primeiro)
    return db.query(Champion).order_by(Champion.titles.desc()).all()

@app.post("/champions/add")
def add_champion(payload: PlayerCreate, db: Session = Depends(get_db)):
    # Verifica se já foi campeão antes
    champ = db.query(Champion).filter(Champion.name == payload.name).first()
    if champ:
        champ.titles += 1 # Adiciona +1 Troféu
    else:
        # Novo campeão
        new_champ = Champion(name=payload.name, titles=1)
        db.add(new_champ)

    db.commit()
    return {"message": f"{payload.name} consagrado campeão!"}