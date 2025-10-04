import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import pandas as pd
import os

def plot_monthly_variable(month, years, values, var_name, unit):
    os.makedirs(f"./result/{var_name}", exist_ok=True)
    df = pd.DataFrame({
        "year": years,
        var_name: values
    })
    
    plt.figure(figsize=(8,5))
    
    if var_name in ["precipitation"]:
        plt.bar(df["year"], df[var_name], color="skyblue")
    else:
        plt.plot(df["year"], df[var_name], marker='o', linewidth=2,
                 color={'temperature':'orange','humidity':'teal','windspeed':'purple'}.get(var_name,'gray'))
        plt.scatter(df["year"], df[var_name], s=60)
    
    plt.title(f"{month} {var_name.replace('_',' ').title()} ({years[0]}–{years[-1]})")
    plt.xlabel("Year")
    plt.ylabel(f"{var_name.replace('_',' ').title()} ({unit})")
    plt.xticks(df["year"])
    plt.tight_layout()
    plt.savefig(f"./result/{var_name}/{month}_{var_name}.png")
    plt.close()


years = [2021, 2022, 2023, 2024, 2025]
month = "January"

plot_monthly_variable(month, years, [24.1, 23.5, 25.2, 26.0, 24.8], "temperature", "°C")
plot_monthly_variable(month, years, [120, 85, 110, 132, 90], "precipitation", "mm")
plot_monthly_variable(month, years, [68, 70, 72, 66, 69], "humidity", "%")
plot_monthly_variable(month, years, [2.7, 3.0, 2.5, 2.9, 3.2], "windspeed", "m/s")
plot_monthly_variable(month, years, [50, 42, 58, 47, 55], "air_quality", "μg/m³")
