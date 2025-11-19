from enum import Enum

class Emotion(str, Enum):
    neutral = "neutral"
    happy = "happy"
    sad = "sad"
    anger = "anger"
    fear = "fear"
    surprise = "surprise"
    disgust = "disgust"
