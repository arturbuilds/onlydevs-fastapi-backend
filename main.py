from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as redis
import json
import os
from dotenv import load_dotenv
load_dotenv()

from database import get_async_db, engine, Base
import models
import schemas

app = FastAPI()

redis_client = redis.Redis(
    host=os.getenv('redis_host'),
    port=6379,
    password=os.getenv('redis_password'),
    ssl=True,
    decode_responses=True
)

@app.on_event('startup')
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post('/authors/')
async def create_author(author_data: schemas.AuthorCreate, db: AsyncSession = Depends(get_async_db)):
    query = select(models.Author).where(models.Author.username == author_data.username)

    result = await db.execute(query)
    existing_author = result.scalars().first()
    if existing_author:
        raise HTTPException(status_code=400, detail="Этот юзернейм уже занят")
    
    new_author = models.Author(username=author_data.username)
    db.add(new_author)
    await db.commit()
    await db.refresh(new_author)
    return new_author

@app.post('/posts/')
async def create_post(post_data: schemas.PostCreate, db: AsyncSession = Depends(get_async_db)):
    query = select(models.Author).where(models.Author.id == post_data.author_id)
    
    result = await db.execute(query)
    author_exists = result.scalars().first()
    if not author_exists:
        raise HTTPException(status_code=404, detail='Такой автор не найден. Сначала создайте автора!')
    
    new_post = models.Post(
        title=post_data.title,
        secret_content=post_data.secret_content,
        price=post_data.price,
        author_id=post_data.author_id
    )

    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)

    await redis_client.delete('all_posts')

    return new_post

@app.get('/posts/')
async def get_posts(db: AsyncSession = Depends(get_async_db)):
    cached_posts = await redis_client.get('all_posts')

    if cached_posts:
        return json.loads(cached_posts)

    query = select(models.Post.id, models.Post.title, models.Post.price, models.Post.author_id)
    result = await db.execute(query)
    posts = result.all()

    posts_list = [{"id": p.id, "title": p.title, "price": p.price, "author_id": p.author_id} for p in posts]

    await redis_client.set('all_posts', json.dumps(posts_list), ex=60)

    return posts_list

@app.post('/posts/{post_id}/buy')
async def buy_post(post_id: int, user_id: int, db: AsyncSession = Depends(get_async_db)):
    query_post = select(models.Post).where(models.Post.id == post_id)
    result_post = await db.execute(query_post)
    existing_post = result_post.scalars().first()
    if not existing_post:
        raise HTTPException(status_code=404, detail='Пост не найден')
    
    query_purchase = select(models.Purchase).where(models.Purchase.user_id == user_id, models.Purchase.post_id == post_id)
    result_purchase = await db.execute(query_purchase)
    isPurchase = result_purchase.scalars().first()
    if isPurchase:  
        raise HTTPException(status_code=400, detail='Вы уже купили этот пост')
    
    query_author = select(models.Author).where(models.Author.id == existing_post.author_id)
    result = await db.execute(query_author)
    author = result.scalars().first()
    author.balance += existing_post.price

    new_purchase = models.Purchase(
        user_id=user_id,
        post_id=post_id
    )

    db.add(new_purchase)
    await db.commit()
    await db.refresh(new_purchase)

    return {"status": "success", "message": "Покупка успешно оформлена", "purchase_id": new_purchase.id}

@app.get('/posts/{post_id}')
async def get_post(post_id: int, user_id: int, db: AsyncSession = Depends(get_async_db)):
    cached_post = await redis_client.get(f'post_{post_id}')

    if cached_post:
        print("🎰 ВАУ! ДАННЫЕ ВЗЯТЫ ИЗ ОБЛАЧНОГО REDIS!")
        post_dict = json.loads(cached_post)
    else:
        print("💿 ОЙ, В РЕДИСЕ ПУСТО, ИДУ В СИНХРОННУЮ/АСИНХРОННУЮ БД SQLite...")
        query_post = select(models.Post).where(models.Post.id == post_id)
        result_post = await db.execute(query_post)
        post = result_post.scalars().first()

        if not post:
            raise HTTPException(status_code=404, detail='Такого поста нет')
        
        post_dict = {
            "id": post.id,
            "title": post.title,
            "secret_content": post.secret_content,
            "price": post.price,
            "author_id": post.author_id
        }

        await redis_client.set(f'post_{post_id}', json.dumps(post_dict), ex=60)

    query_purchased = select(models.Purchase).where(models.Purchase.user_id == user_id, models.Purchase.post_id == post_id)
    result_purchased = await db.execute(query_purchased)
    is_purchased = result_purchased.scalars().first()

    if post_dict['price'] == 0 or is_purchased:
        return post_dict
    else:
        raise HTTPException(status_code=403, detail='Доступ запрещен. Купите пост')