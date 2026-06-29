from sqlalchemy import Column, Integer, String, ForeignKey
from database import Base

class Author(Base):
    __tablename__ = 'authors'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True, nullable=False)
    balance = Column(Integer, default=0)
    bio = Column(String, nullable=True)

class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    secret_content = Column(String, nullable=False)
    price = Column(Integer, default=0)
    author_id = Column(Integer, ForeignKey('authors.id'))
    views = Column(Integer, default=0)

class Purchase(Base):
    __tablename__ = 'purchases'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id'))