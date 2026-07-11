# a = int(input("Enter first number: "))
# b = int(input("Enter second number: "))
# c = int(input("Enter third number: "))
# d = int(input("Enter forth number: "))

# if (a >= b and a >= c and a >= d):
#     print("first number is largest", a)
# elif (b >= c and b >= d):
#     print("second number is largest", b)

# elif (c >= d):
#     print("third number is largest", c)
# else:
#     print("forth is largest", d)

# Name = (input("Enter your name: "))
# Age = int(input("Enter your age: "))
# Number = int(input("Enter the number: "))

# print(f"Hello! My name is {Name}, that's my age {Age}, It is number {Number}. ")

# year = int(input("tell your year: "))

# if year % 100 == 0 and year % 400 == 0:
#     print("It's a leap year")
    
# elif year % 100 != 0 and year % 4 == 0:
#     print("It's a leap year")
    
# else:
#     print("It's a normal year")

# numbers = [5, 2, 9, 1, 5, 6] # Initial list

# numbers.append(10)
# numbers.insert(2, 15)
# numbers.extend([20, 25, 30])
# numbers.remove(5)
# numbers.pop(6)
# index = numbers.index(9)
# count_5 = numbers.count(5)
# numbers.sort()
# numbers.reverse()
# new_numbers = numbers.copy()
# numbers.clear()

# print(numbers)

p = open('lecture2.py')

print(p.read())