from fastapi import FastAPI
from api.routers import users, auth, events, admin, form_templates, uploads, notifications, payments, email_templates, feedback_templates, feedback, ai_summaries
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
    app.include_router(email_templates.router, prefix="/email-templates", tags=["Email Templates"])
    app.include_router(feedback_templates.router, prefix="/feedback-templates", tags=["Feedback Templates"])
    app.include_router(feedback.router, prefix="/events", tags=["Feedback"])
    app.include_router(uploads.router, prefix="/uploads", tags=["Uploads"])
    app.include_router(notifications.router, prefix="", tags=["Notifications"])
    app.include_router(payments.router, prefix="/payments", tags=["Payments"])
    app.include_router(ai_summaries.router)






    @app.get("/")
    def read_root():
        """Root server confirmation"""
        return {"message": "Successfully started the server"}   
    
    return app 
