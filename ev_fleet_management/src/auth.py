from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from ev_fleet_management.utils.db import get_db
from ev_fleet_management.utils.jwt_helper import create_access_token, get_current_user_from_cookie
from ev_fleet_management.model.models import UserModel, DriverModel, EVModel, UserRegister, UserLogin, UserOut
from ev_fleet_management.exception.custom_exception import AuthenticationError, ValidationError, EntityNotFoundError
from ev_fleet_management.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Check if username (id) or email already exists
    existing_user = db.query(UserModel).filter(
        (UserModel.id == user_data.id) | (UserModel.email == user_data.email)
    ).first()
    if existing_user:
        raise ValidationError("Username or Email already registered")

    # Create new user
    new_user = UserModel(
        id=user_data.id,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
        is_verified=False
    )
    db.add(new_user)

    # If user is a driver, create driver details
    if user_data.role == "driver":
        # Check if vehicle exists
        vehicle = None
        if user_data.vehicle_id:
            vehicle = db.query(EVModel).filter(EVModel.id == user_data.vehicle_id).first()
            if not vehicle:
                # Dynamically create EV model if not exists to make testing smoother
                vehicle = EVModel(
                    id=user_data.vehicle_id,
                    make="Volkswagen",
                    model="Fleet Spec",
                    plate_no=f"EV-{user_data.id}-TN",
                    battery_capacity_kwh=52.0,
                    year=2024,
                    odometer_km=1000.0,
                    battery_health_soh=100.0,
                    next_service_km=2818.0,
                    status="Idle"
                )
                db.add(vehicle)

        new_driver = DriverModel(
            id=user_data.id,
            name=user_data.name,
            email=user_data.email,
            user_id=user_data.id,
            vehicle_id=vehicle.id if vehicle else None,
            status="Idle"
        )
        db.add(new_driver)

    db.commit()

    # Generate verification token (simple string format for mock url)
    verify_token = f"verify_{user_data.id}"
    verify_link = f"http://127.0.0.1:8000/api/auth/verify/{verify_token}"
    logger.info(f"📧 Mock Email Verification dispatched to {user_data.email}!")
    logger.info(f"👉 CLICK TO VERIFY ACCOUNT: {verify_link}")

    return {"message": "Registration successful. Please verify email via link in server console logs.", "verification_link": verify_link}

@router.post("/login")
def login(login_data: UserLogin, response: Response, db: Session = Depends(get_db)):
    # Find user
    user = db.query(UserModel).filter(UserModel.email == login_data.email).first()
    if not user:
        # Check if user entered ID instead of email
        user = db.query(UserModel).filter(UserModel.id == login_data.id).first()
        
    if not user or not verify_password(login_data.password, user.password_hash):
        raise AuthenticationError("Incorrect ID/email or password")

    if not user.is_verified:
        raise AuthenticationError("Please verify your email before logging in. Check server logs.")

    # Create JWT
    token = create_access_token(data={"sub": user.id, "role": user.role})
    
    # Set HTTPOnly Cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=3600 * 24, # 1 day
        samesite="lax"
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "id": user.id,
        "email": user.email
    }

@router.get("/verify/{token}")
def verify_email(token: str, db: Session = Depends(get_db)):
    if not token.startswith("verify_"):
        raise ValidationError("Invalid verification token")
    
    user_id = token.replace("verify_", "")
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise EntityNotFoundError("User not found")

    user.is_verified = True
    db.commit()
    return {"message": "Account successfully verified! You can now sign in."}

@router.get("/me", response_model=UserOut)
def get_me(current_user: dict = Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == current_user["sub"]).first()
    if not user:
        raise EntityNotFoundError("User session not found")
    return user

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Successfully signed out"}
