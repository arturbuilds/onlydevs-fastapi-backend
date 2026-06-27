from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

database_url = 'sqlite:///./only_devs.db'
engine = create_engine(database_url, connect_args={'check_same_thread': False})

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Author(Base):
    __tablename__ = 'authors'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True, nullable=False)
    balance = Column(Integer, default=0)

class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    secret_content = Column(String, nullable=False)
    price = Column(Integer, default=0)
    author_id = Column(Integer, ForeignKey('authors.id'))

class Purchase(Base):
    __tablename__ = 'purchases'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id'))

Base.metadata.create_all(bind=engine)

class AuthorCreate(BaseModel):
    username: str

class PostCreate(BaseModel):
    title: str
    secret_content: str
    price: int
    author_id: int

app = FastAPI(title="OnlyDevs API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post('/authors/')
def create_author(author_data: AuthorCreate, db: Session = Depends(get_db)):
    existing_author = db.query(Author).filter(Author.username == author_data.username).first()
    if existing_author:
        raise HTTPException(status_code=400, detail="Этот юзернейм уже занят")
    
    new_author = Author(username=author_data.username)
    db.add(new_author)
    db.commit()
    db.refresh(new_author)
    return new_author

@app.post('/posts/')
def create_post(post_data: PostCreate, db: Session = Depends(get_db)):
    author_exists = db.query(Author).filter(Author.id == post_data.author_id).first()
    if not author_exists:
        raise HTTPException(status_code=404, detail='Такой автор не найден. Сначала создайте автора!')
    
    new_post = Post(
        title=post_data.title,
        secret_content=post_data.secret_content,
        price=post_data.price,
        author_id=post_data.author_id
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post

@app.get('/posts/')
def get_posts(db: Session = Depends(get_db)):
    posts = db.query(Post.id, Post.title, Post.price, Post.author_id).all()
    return [{"id": p.id, "title": p.title, "price": p.price, "author_id": p.author_id} for p in posts]

@app.post('/posts/{post_id}/buy')
def buy_post(post_id: int, user_id: int, db: Session = Depends(get_db)):
    existing_post = db.query(Post).filter(Post.id == post_id).first()
    if not existing_post:
        raise HTTPException(status_code=404, detail='Пост не найден')
    
    isPurchase = db.query(Purchase).filter(Purchase.user_id == user_id, Purchase.post_id == post_id).first()
    if isPurchase:  
        raise HTTPException(status_code=400, detail='Вы уже купили этот пост')
    
    author = db.query(Author).filter(Author.id == existing_post.author_id).first()
    author.balance += existing_post.price

    new_purchase = Purchase(
        user_id=user_id,
        post_id=post_id
    )

    db.add(new_purchase)
    db.commit()
    db.refresh(new_purchase)

    return {"status": "success", "message": "Покупка успешно оформлена", "purchase_id": new_purchase.id}

@app.get('/posts/{post_id}')
def get_post(post_id: int, user_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail='Такого поста нет')
    
    is_purchased = db.query(Purchase).filter(
        Purchase.user_id == user_id, 
        Purchase.post_id == post_id
    ).first()

    if post.price == 0 or is_purchased:
        return post
    else:
        raise HTTPException(status_code=403, detail='Доступ запрещен. Купите пост')
