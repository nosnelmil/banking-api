import time
from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError, ExpiredSignatureError
from auth import SECRET_KEY, ALGORITHM
 
def make_token(username, minutes=5):
    # build a payload with sub, iat and exp, return the signed token
    payload = {
        "sub": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=minutes)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
 
def show_token(token):
    payload = jwt.decode(
        token,
        SECRET_KEY,
        options={"verify_signature": False}
    )

    user = payload.get("sub", "Unknown")

    sg_timezone = timezone(timedelta(hours=8))
    exp = datetime.fromtimestamp(payload["exp"], tz=sg_timezone)
    iat = datetime.fromtimestamp(payload["iat"], tz=sg_timezone)
    seconds_left = (exp - datetime.now(sg_timezone)).total_seconds()

    print(f"user: {user}, issued: {iat}, expiry: {exp}")
    print(f"seconds left: {int(seconds_left)}" if seconds_left > 0 else "EXPIRED")


def check_token(token):
    try:
        jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return "valid"

    except ExpiredSignatureError:
        return "expired"

    except JWTError:
        return "invalid"


if __name__ == "__main__":
    good = make_token("yourname", 5)
    show_token(good)
    print("good token     :", check_token(good))
    print("expired token  :", check_token(make_token("yourname", -1)))
    print("tampered token :", check_token(good[:-3] + "abc"))
    other = jwt.encode({"sub": "yourname"}, "some-other-secret", algorithm=ALGORITHM)
    print("wrong secret   :", check_token(other))
