number = 1
number2 = 1.0
greeting = "こんにちは"
is_ok = True

print(number, type(number))
print(number2, type(number2))
print(greeting, type(greeting))
print(is_ok, type(is_ok))

print(1 < 2)
print(1 > 2)

print("Hello")

print(1 + 2)

print("テストの点数は" + str(100) + "点です")

score = 90
if score <  90:
    print("合格")

elif score > 50:
    print("再試験")

else:
    print("不合格")