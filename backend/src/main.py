"""
Terças FC - Football League Management API
Backend service built with FastAPI and SQLAlchemy.
Handles player management, match recording, automated leaderboard calculations, and financial tracking.
"""

import os
import json
import enum
from datetime import date
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel
from datetime import datetime, timedelta

# =============================================================================
# Game Settings
# =============================================================================

MATCH_DAY = 1           # O jogo é à Terça
MATCH_HOUR = 22         # 22 horas
MATCH_MINUTE = 30       # 30 minutos

# Abertura da Convocatória
OPEN_DAY = 2            # Quarta-feira 
OPEN_HOUR = 9          # 09:00 da manhã

# Fecho da Convocatória: Terça-feira (1)
CLOSE_DAY = 1           # Própria Terça
CLOSE_HOUR = 19         # 19:00

# =============================================================================
# 1. DATABASE CONFIGURATION & SETUP
# =============================================================================

# Retrieve database URL from environment variables. Defaults to SQLite for local development.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./football.db")

# Compatibility fix: SQLAlchemy requires 'postgresql://', but some providers return 'postgres://'
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Logging connection type for debugging purposes
if "sqlite" in DATABASE_URL:
    print("⚠️ WARNING: Running with SQLite (Ephemeral Data). Data will be lost on restart.")
else:
    print(f"✅ SUCCESS: Connected to production database (PostgreSQL).")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =============================================================================
# 2. SQLALCHEMY ORM MODELS
# =============================================================================
class MatchResult(str, enum.Enum):
    """Enum representing possible outcomes of a match."""
    TEAM_A = "TEAM_A"
    TEAM_B = "TEAM_B"
    DRAW = "DRAW"

class MatchPlayer(Base):
    """Association table linking matches and players, storing team assignment."""
    __tablename__ = "match_players"
    match_id = Column(Integer, ForeignKey("matches.id"), primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), primary_key=True)
    team = Column(String, nullable=False)

class Attendance(Base):
    """Tracks player attendance for upcoming matches."""
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    status = Column(String)

class Player(Base):
    """
    Represents a player in the league.
    Distinguishes between 'Fixed' players (pay monthly) and 'Guests' (pay per game).
    """
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    username = Column(String, unique=True, nullable=True)
    password = Column(String, nullable=True)
    role = Column(String, default="player")
    is_active = Column(Boolean, default=True)
    balance = Column(Float, default=0.0)
    is_fixed = Column(Boolean, default=False)
    previous_rank = Column(Integer, default=0)
    matches = relationship("Match", secondary="match_players", back_populates="players")

class Match(Base):
    """Represents a single match event."""
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    result = Column(String, nullable=True)
    is_double_points = Column(Boolean, default=False)
    status = Column(String, default="concluido") # 'agendado', 'concluido'
    time = Column(String, nullable=True)
    location = Column(String, nullable=True)
    opponent = Column(String, nullable=True)
    players = relationship("Player", secondary="match_players", back_populates="matches")

class Champion(Base):
    """Tracks historical title winners."""
    __tablename__ = "champions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    titles = Column(Integer, default=1)

class SeasonArchive(Base):
    """Archives past season stats (JSON snapshot) for historical reference."""
    __tablename__ = "season_archive"
    id = Column(Integer, primary_key=True, index=True)
    season_name = Column(String)
    data_json = Column(Text)
    date = Column(Date)

# Create tables if they do not exist
Base.metadata.create_all(bind=engine)

# =============================================================================
# 3. PYDANTIC SCHEMAS (Data Validation)
# =============================================================================
class LoginRequest(BaseModel):
    username: str
    password: str
class PlayerCreate(BaseModel):
    name: str
    is_fixed: bool = False

class PlayerStatusUpdate(BaseModel):
    """Schema for updating player status (Fixed/Guest)."""
    is_fixed: bool

class PaymentSchema(BaseModel):
    player_id: int
    amount: float

class PlayerSchema(BaseModel):
    id: int
    name: str
    balance: float
    is_active: bool
    is_fixed: bool
    previous_rank: int
    class Config:
        from_attributes = True

class MatchCreate(BaseModel):
    date: date
    result: MatchResult
    team_a_players: List[int]
    team_b_players: List[int]
    goalkeepers: List[int] = []
    is_double_points: bool = False

class ChampionSchema(BaseModel):
    name: str
    titles: int
    class Config:
        from_attributes = True

class CloseSeasonSchema(BaseModel):
    season_name: str

class ArchiveSchema(BaseModel):
    id: int
    season_name: str
    date: date
    data_json: str
    class Config:
        from_attributes = True

class AttendanceRequest(BaseModel):
    match_id: int
    player_id: int
    status: str  # "going", "not_going"

# =============================================================================
# 4. BUSINESS LOGIC & API ENDPOINTS
# =============================================================================

app = FastAPI(
    title="Terças FC API V4.4",
    description="REST API for managing a recreational football league.",
    version="4.4.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # O asterisco significa "Toda a gente pode entrar"
    allow_credentials=True,
    allow_methods=["*"],  # Permite GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],
)

def get_db():
    """Dependency to provide a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- FUNÇÕES AUXILIARES (DATAS) ---

def get_next_tuesday_date():
    """Calcula a data e hora da próxima Terça-feira às 22h30."""
    now = datetime.now()
    days_ahead = MATCH_DAY - now.weekday()
    
    # Se já passou a hora do jogo de hoje, salta para a próxima semana
    if days_ahead < 0 or (days_ahead == 0 and now.hour > MATCH_HOUR):
        days_ahead += 7
        
    next_date = now + timedelta(days=days_ahead)
    return next_date.replace(hour=MATCH_HOUR, minute=MATCH_MINUTE, second=0, microsecond=0)

def is_convocation_open(match_datetime):
    """Verifica se estamos dentro da janela de abertura/fecho."""
    now = datetime.now()
    
    # Calcular Abertura
    days_back_open = (match_datetime.weekday() - OPEN_DAY) % 7
    if days_back_open == 0 and OPEN_DAY != MATCH_DAY: 
        days_back_open = 7

    open_date = match_datetime - timedelta(days=days_back_open)
    open_date = open_date.replace(hour=OPEN_HOUR, minute=0, second=0)

    # Calcular Fecho
    close_date = match_datetime.replace(hour=CLOSE_HOUR, minute=0, second=0)

    return open_date <= now <= close_date, open_date, close_date

# ----------------------------------

def calculate_table_stats(db: Session) -> List[Dict[str, Any]]:
    """
    Calculates the live leaderboard based on match history.
    Only 'Fixed' players appear on the main leaderboard.
    """
    players = db.query(Player).filter(Player.is_active == True, Player.is_fixed == True).all()
    matches = db.query(Match).order_by(Match.date).all()

    stats = {p.id: {
        "id": p.id, "name": p.name,
        "games_played": 0, "wins": 0, "draws": 0, "losses": 0, "points": 0,
        "form": [], "previous_rank": p.previous_rank, "is_fixed": p.is_fixed
    } for p in players}

    for m in matches:
        multiplier = 2 if m.is_double_points else 1
        links = db.query(MatchPlayer).filter(MatchPlayer.match_id == m.id).all()

        for link in links:
            pid = link.player_id
            if pid not in stats: continue

            stats[pid]["games_played"] += 1
            res_char = ""

            if m.result == "DRAW":
                stats[pid]["draws"] += 1
                stats[pid]["points"] += (2 * multiplier)
                res_char = "D"
            elif (m.result == "TEAM_A" and link.team == "A") or (m.result == "TEAM_B" and link.team == "B"):
                stats[pid]["wins"] += 1
                stats[pid]["points"] += (3 * multiplier)
                res_char = "W"
            else:
                stats[pid]["losses"] += 1
                stats[pid]["points"] += (1 * multiplier)
                res_char = "L"

            stats[pid]["form"].append(res_char)

    res = list(stats.values())
    for p in res:
        p["form"] = p["form"][-5:]

    # Sorting Logic: Points (Desc) -> Games (Desc) -> Previous Rank (Asc/Lower is better)
    res.sort(
        key=lambda x: (
            x["points"],
            x["games_played"],
            -x["previous_rank"] if x["previous_rank"] > 0 else -999999
        ),
        reverse=True
    )
    return res

# -- ENDPOINTS --

@app.get("/table/", response_model=List[Dict[str, Any]])
def get_table(db: Session = Depends(get_db)):
    """Returns the calculated leaderboard for the current season."""
    return calculate_table_stats(db)

@app.get("/matches/next")
def get_next_match(db: Session = Depends(get_db)):
    now = datetime.now()
    str_now = now.strftime("%Y-%m-%d")

    # 1. Procura jogo
    next_match = db.query(Match)\
        .filter(Match.status == "agendado")\
        .filter(Match.date >= str_now)\
        .order_by(Match.date.asc())\
        .first()

    # 2. Se não existir, CRIA para a próxima terça
    if not next_match:
        target_date = get_next_tuesday_date()
        date_str = target_date.strftime("%Y-%m-%d")
        
        exists = db.query(Match).filter(Match.date == date_str).first()
        
        if not exists:
            next_match = Match(
                date=date_str,
                time=f"{MATCH_HOUR}:{MATCH_MINUTE}",
                location="Campo Principal",
                opponent="Jogo Interno",
                status="agendado"
            )
            db.add(next_match)
            db.commit()
            db.refresh(next_match)
        else:
            next_match = exists

    match_dt = datetime.strptime(f"{next_match.date} {next_match.time}", "%Y-%m-%d %H:%M")
    
    is_open, open_dt, close_dt = is_convocation_open(match_dt) 
    
    confirmed_count = db.query(Attendance)\
        .filter(Attendance.match_id == next_match.id, Attendance.status == "going")\
        .count()

    return {
        "id": next_match.id,
        "date": next_match.date,
        "time": next_match.time,
        "location": next_match.location,
        "opponent": next_match.opponent,
        "confirmed_players": confirmed_count,
        "is_open": is_open,
        "close_date": close_dt.isoformat()
    }

# Endpoint to confirme presence
@app.post("/matches/attend")
def update_attendance(data: AttendanceRequest, db: Session = Depends(get_db)):
    # CORREÇÃO: Removemos o "models." antes de Match
    match = db.query(Match).filter(Match.id == data.match_id).first()
    
    if not match:
        return {"success": False, "message": "Jogo não encontrado"}

    # CORREÇÃO: Removemos o "models." antes de Attendance
    attendance = db.query(Attendance).filter(
        Attendance.match_id == data.match_id,
        Attendance.player_id == data.player_id
    ).first()

    if attendance:
        attendance.status = data.status # Atualiza (mudou de ideias)
    else:
        # CORREÇÃO: Removemos o "models." aqui também
        attendance = Attendance(
            match_id=data.match_id,
            player_id=data.player_id,
            status=data.status
        )
        db.add(attendance)
    
    db.commit()
    return {"success": True, "message": "Presença guardada!"}

# -- Login Endpoint --
@app.post("/login")
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    # 1. Procura o jogador pelo username
    player = db.query(Player).filter(Player.username == login_data.username).first()
    
    # 2. Verifica se existe e se a senha bate certo
    if not player or player.password != login_data.password:
        return {"success": False, "message": "Dados errados"}
    
    # 3. Sucesso! Devolve os dados dele
    return {
        "success": True,
        "player_id": player.id,
        "name": player.name,
        "role": player.role,
        "message": "Bem-vindo!"
    }
   
@app.post("/players/", response_model=PlayerSchema)
def create_player(player: PlayerCreate, db: Session = Depends(get_db)):
    """Registers a new player."""
    if db.query(Player).filter(Player.name == player.name).first():
        raise HTTPException(400, "Player already exists")

    new_player = Player(
        name=player.name,
        balance=0.0,
        is_active=True,
        is_fixed=player.is_fixed,
        previous_rank=0
    )
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    return new_player

@app.put("/players/{player_id}/status")
def update_player_status(player_id: int, status: PlayerStatusUpdate, db: Session = Depends(get_db)):
    """Updates a player's status (Fixed vs Guest)."""
    p = db.query(Player).filter(Player.id == player_id).first()
    if not p:
        raise HTTPException(404, "Player not found")

    p.is_fixed = status.is_fixed
    db.commit()
    return {"message": "Player status updated successfully"}

@app.get("/players/", response_model=List[PlayerSchema])
def read_players(db: Session = Depends(get_db)):
    """Returns all active players."""
    return db.query(Player).filter(Player.is_active == True).all()

@app.get("/players/all", response_model=List[PlayerSchema])
def read_all_players(db: Session = Depends(get_db)):
    """Returns all players including inactive ones."""
    return db.query(Player).all()

@app.post("/players/pay")
def register_payment(payment: PaymentSchema, db: Session = Depends(get_db)):
    """Registers a monetary payment."""
    p = db.query(Player).filter(Player.id == payment.player_id).first()
    if not p:
        raise HTTPException(404, "Player not found")
    p.balance += payment.amount
    db.commit()
    return {"message": "Payment successful"}

@app.post("/players/charge_monthly")
def charge_monthly_fees(db: Session = Depends(get_db)):
    """Charges monthly fee to all fixed players."""
    fixed_players = db.query(Player).filter(Player.is_fixed == True).all()
    count = 0
    for p in fixed_players:
        p.balance -= 14.0
        count += 1
    db.commit()
    return {"message": f"Charged monthly fee to {count} fixed players"}

@app.post("/matches/")
def create_match(match: MatchCreate, db: Session = Depends(get_db)):
    """Records a match result and applies financial logic."""
    db_match = Match(date=match.date, result=match.result, is_double_points=match.is_double_points)
    db.add(db_match)
    db.commit()
    db.refresh(db_match)

    all_pids = match.team_a_players + match.team_b_players

    for pid in all_pids:
        team = "A" if pid in match.team_a_players else "B"
        db.add(MatchPlayer(match_id=db_match.id, player_id=pid, team=team))

        if pid not in match.goalkeepers:
            p = db.query(Player).filter(Player.id == pid).first()
            if p and not p.is_fixed:
                p.balance -= 3.0

    db.commit()
    return {"message": "Match created successfully"}

# -- CHAMPIONS & HISTORY MANAGEMENT --

@app.get("/champions/", response_model=List[ChampionSchema])
def get_champions(db: Session = Depends(get_db)):
    """Returns list of past champions."""
    return db.query(Champion).order_by(Champion.titles.desc()).all()

@app.post("/champions/remove")
def remove_champion(data: PlayerCreate, db: Session = Depends(get_db)):
    """Manually removes a title from a player."""
    champ = db.query(Champion).filter(Champion.name == data.name).first()
    if not champ:
        raise HTTPException(404, "Champion not found")

    if champ.titles > 1:
        champ.titles -= 1
    else:
        db.delete(champ)

    db.commit()
    return {"message": "Title removed"}

@app.post("/season/close")
def close_season(data: CloseSeasonSchema, db: Session = Depends(get_db)):
    """Closes the current season and archives data."""
    final_stats = calculate_table_stats(db)
    if not final_stats:
        raise HTTPException(400, "No match data available")

    champion_name = final_stats[0]["name"]

    champ = db.query(Champion).filter(Champion.name == champion_name).first()
    if champ:
        champ.titles += 1
    else:
        db.add(Champion(name=champion_name, titles=1))

    for index, player_stat in enumerate(final_stats):
        p = db.query(Player).filter(Player.id == player_stat['id']).first()
        if p:
            p.previous_rank = index + 1

    archive = SeasonArchive(
        season_name=f"{data.season_name} ({date.today()})",
        date=date.today(),
        data_json=json.dumps(final_stats)
    )
    db.add(archive)

    db.query(MatchPlayer).delete()
    db.query(Match).delete()
    db.commit()

    return {"message": f"Season closed successfully! Champion: {champion_name}"}

@app.get("/history/", response_model=List[ArchiveSchema])
def get_history(db: Session = Depends(get_db)):
    """Returns archived season data."""
    return db.query(SeasonArchive).order_by(SeasonArchive.date.desc()).all()

@app.delete("/history/{archive_id}")
def delete_history_entry(archive_id: int, db: Session = Depends(get_db)):
    """Deletes a specific archived season."""
    archive = db.query(SeasonArchive).filter(SeasonArchive.id == archive_id).first()
    if not archive:
        raise HTTPException(404, "History entry not found")
    db.delete(archive)
    db.commit()
    return {"message": "Deleted"}

@app.delete("/reset/")
def reset_manual(db: Session = Depends(get_db)):
    """Emergency reset button for development."""
    db.query(MatchPlayer).delete()
    db.query(Match).delete()
    db.commit()
    return {"message": "Reset done"}