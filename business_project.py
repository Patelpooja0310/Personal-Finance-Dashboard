import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import numpy as np
import os

# -----------------------------
# FILE CHECK
# -----------------------------
file_name = "business_data.csv"

if not os.path.exists(file_name):
    print("Error: CSV file not found!")
    exit()

# -----------------------------
# LOAD DATA
# -----------------------------
data = pd.read_csv(file_name)

# -----------------------------
# DATA PROCESSING
# -----------------------------
data["Profit"] = data["Sales"] - data["Expenses"]

# -----------------------------
# FUNCTIONS
# -----------------------------
def show_data():
    print("\n===== BUSINESS DATA =====")
    print(data)

def summary():
    print("\n===== SUMMARY REPORT =====")
    print("Total Sales:", data["Sales"].sum())
    print("Total Expenses:", data["Expenses"].sum())
    print("Total Profit:", data["Profit"].sum())
    print("Average Sales:", int(data["Sales"].mean()))

def sales_graph():
    plt.figure()
    plt.plot(data["Month"], data["Sales"], marker="o")
    plt.title("Monthly Sales Trend")
    plt.xlabel("Month")
    plt.ylabel("Sales")
    plt.show()

def expense_graph():
    plt.figure()
    plt.bar(data["Month"], data["Expenses"])
    plt.title("Monthly Expenses")
    plt.xlabel("Month")
    plt.ylabel("Expenses")
    plt.show()

def profit_graph():
    plt.figure()
    plt.plot(data["Month"], data["Profit"], marker="o")
    plt.title("Monthly Profit")
    plt.xlabel("Month")
    plt.ylabel("Profit")
    plt.show()

def predict_sales():
    x = np.arange(len(data)).reshape(-1,1)
    y = data["Sales"]

    model = LinearRegression()
    model.fit(x,y)

    next_month = len(data)
    prediction = model.predict([[next_month]])

    print("\nPredicted Next Month Sales =", int(prediction[0]))

def save_report():
    report = f"""
Business Report
------------------------
Total Sales: {data["Sales"].sum()}
Total Expenses: {data["Expenses"].sum()}
Total Profit: {data["Profit"].sum()}
Average Sales: {int(data["Sales"].mean())}
"""
    with open("report.txt","w") as f:
        f.write(report)

    print("Report saved as report.txt")

# -----------------------------
# MENU SYSTEM
# -----------------------------
while True:
    print("""
========= BUSINESS DASHBOARD =========
1. Show Data
2. Summary Report
3. Sales Graph
4. Expense Graph
5. Profit Graph
6. Predict Next Month Sales
7. Save Report
8. Exit
""")

    choice = input("Enter choice: ")

    if choice == "1":
        show_data()

    elif choice == "2":
        summary()

    elif choice == "3":
        sales_graph()

    elif choice == "4":
        expense_graph()

    elif choice == "5":
        profit_graph()

    elif choice == "6":
        predict_sales()

    elif choice == "7":
        save_report()

    elif choice == "8":
        print("Program Closed")
        break

    else:
        print("Invalid Choice — Try Again")