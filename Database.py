from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(200), nullable=False)

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    project_name = Column(String(200), nullable=False)
    original_image = Column(String(500), nullable=False)
    generated_image = Column(String(500), nullable=False)
    style = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    customizations = Column(Text)

engine = create_engine('sqlite:///smartspace.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
