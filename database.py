from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
load_dotenv()

RENDER_DATABASE_URL = os.getenv("DATABASE_INDIA")
engine = create_engine(RENDER_DATABASE_URL)
Session = sessionmaker(bind=engine)