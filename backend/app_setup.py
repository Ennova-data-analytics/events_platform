from fastapi import FastAPI
from api.routers import users, auth, events, admin, form_templates, uploads, notifications
from middleware import setup_middleware

def create_app() -> FastAPI:
    """Application factory"""
    app = FastAPI(title="Events Management Platform API")
    app = setup_middleware(app)
    app.include_router(users.router, prefix="/users", tags=["Users"])
    app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    app.include_router(events.router, prefix="/events", tags=["Events"])
    app.include_router(admin.router, prefix="/admin", tags=["Admin"])
    app.include_router(form_templates.router, prefix="/form-templates", tags=["Form Templates"])
    app.include_router(uploads.router, prefix="/uploads", tags=["Uploads"])
    app.include_router(notifications.router, prefix="", tags=["Notifications"])






    @app.get("/")
    def read_root():
        """Root server confirmation"""
        return {"message": "Successfully started the server"}   
    
    return app 
