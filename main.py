from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas

app = FastAPI()

@app.post('/authors/')
def create_author(author_data: schemas.AuthorCreate, db: Session = Depends(get_db)):
    existing_author = db.query(models.Author).filter(models.Author.username == author_data.username).first()
    if existing_author:
        raise HTTPException(status_code=400, detail="Этот юзернейм уже занят")
    
    new_author = models.Author(username=author_data.username)
    db.add(new_author)
    db.commit()
    db.refresh(new_author)
    return new_author

@app.post('/posts/')
def create_post(post_data: schemas.PostCreate, db: Session = Depends(get_db)):
    author_exists = db.query(models.Author).filter(models.Author.id == post_data.author_id).first()
    if not author_exists:
        raise HTTPException(status_code=404, detail='Такой автор не найден. Сначала создайте автора!')
    
    new_post = models.Post(
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
    posts = db.query(models.Post.id, models.Post.title, models.Post.price, models.Post.author_id).all()
    return [{"id": p.id, "title": p.title, "price": p.price, "author_id": p.author_id} for p in posts]

@app.post('/posts/{post_id}/buy')
def buy_post(post_id: int, user_id: int, db: Session = Depends(get_db)):
    existing_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not existing_post:
        raise HTTPException(status_code=404, detail='Пост не найден')
    
    isPurchase = db.query(models.Purchase).filter(models.Purchase.user_id == user_id, models.Purchase.post_id == post_id).first()
    if isPurchase:  
        raise HTTPException(status_code=400, detail='Вы уже купили этот пост')
    
    author = db.query(models.Author).filter(models.Author.id == existing_post.author_id).first()
    author.balance += existing_post.price

    new_purchase = models.Purchase(
        user_id=user_id,
        post_id=post_id
    )

    db.add(new_purchase)
    db.commit()
    db.refresh(new_purchase)

    return {"status": "success", "message": "Покупка успешно оформлена", "purchase_id": new_purchase.id}

@app.get('/posts/{post_id}')
def get_post(post_id: int, user_id: int, db: Session = Depends(get_db)):
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail='Такого поста нет')
    
    is_purchased = db.query(models.Purchase).filter(
        models.Purchase.user_id == user_id, 
        models.Purchase.post_id == post_id
    ).first()

    if post.price == 0 or is_purchased:
        return post
    else:
        raise HTTPException(status_code=403, detail='Доступ запрещен. Купите пост')