from pydantic import Field

MAX_CUIT_LENGTH = 11
MIN_CUIT_LENGTH = 10

CUIT_FIELD = Field(..., min_length=MIN_CUIT_LENGTH, max_length=MAX_CUIT_LENGTH)
