s = [3, 5, 7, 12, 18]
t = "Japanese"
print (len(s),len(t))

def add(a, b):
    return a + b

c = add(10,12)
print(c)


def say_hello():
    print("Hello")

x = say_hello()
print(x)

sport = "swimming"
print(sport.count("m"))

import random
lang = ["P", "Y", "T", "H", "O", "N"]
char = random.choice(lang)
print(char)


import math
x = 3.14
print (math.floor(x))
print(math.ceil(x))

import calc
result = calc.calc(3, 4)
print(result)

nums = [i for i in range(10)]
print(nums)