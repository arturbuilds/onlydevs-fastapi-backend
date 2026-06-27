from pydantic import BaseModel

class AuthorCreate(BaseModel):
    username: str

class PostCreate(BaseModel):
    title: str
    secret_content: str
    price: int
    author_id: int
