from pydantic import Field

from mapa_ciencia_unc.models.graph import FilterField

MAX_CUIT_LENGTH = 11
MIN_CUIT_LENGTH = 10

CUIT_FIELD = Field(..., min_length=MIN_CUIT_LENGTH, max_length=MAX_CUIT_LENGTH)


ACADEMIC_UNITS = [
    "FP",
    "FCM",
    "FCQ",
    "FA",
    "FaMAF",
    "FO",
    "FL",
    "FCE",
    "FAUD",
    "FFyH",
    "FCEFyN",
    "FCS",
    "FCA",
    "FCC",
]
ODS = [
    "Objetivo 1: Fin de la pobreza",
    "Objetivo 2: Hambre cero",
    "Objetivo 3: Salud y bienestar",
    "Objetivo 4: Educación de calidad",
    "Objetivo 5: Igualdad de género",
    "Objetivo 6: Agua limpia y saneamiento",
    "Objetivo 7: Energía asequible y no contaminante",
    "Objetivo 8: Trabajo decente y crecimiento económico",
    "Objetivo 9: Industria, innovación e infraestructura",
    "Objetivo 10: Reducir las desigualdades entre países y dentro de ellos",
    "Objetivo 11: Ciudades",
    "Objetivo 12: Producción y consumo sostenibles",
    "Objetivo 13: Cambio climático",
    "Objetivo 14: Océanos",
    "Objetivo 15: Bosques, desertificación y diversidad biológica",
    "Objetivo 16: Paz y justicia",
    "Objetivo 17: Alianzas para lograr los ODS",
]

LANGUAGES = [
    "italiano",
    "aleman",
    "ingles",
    "chino",
    "japones",
    "portugues",
    "coreano",
    "frances",
]
