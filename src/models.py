from sqlalchemy import Column, Integer, String, Date, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from .database import Base

# Define strict options for Match Result to avoid typos like "Vitoria" vs "Win"
class MatchResult(str, enum.Enum):
    TEAM_A = "TEAM_A"
    TEAM_B = "TEAM_B"
    DRAW = "DRAW"

# Define options for wich team a player was on
class TeamSide(str, enum.Enum):
    TEAM_A = "A"
    TEAM_B = "B"

class MatchPlayer(Base):
    """
    Association table (The bridge)
    Links a player to a match and records wich team they played for.
    """
    __tablename__ = "match_players"

    match_id = Column(Integer, ForeignKey("matches.id"), primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), primary_key=True)
    team = Column(String, nullable=False) # We will store "A" or "B"

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    # Relationship: A player has many matches
    matches = relationship("Match", secondary="match_players", back_populates="players")

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    result = Column(String, nullable=False) # Stores team A, team B or draw

    # Relationship: a match as many players
    players= relationship("Player", secondary="match_players", back_populates="matches")
