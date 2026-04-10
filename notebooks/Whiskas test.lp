\* Whiskas *\
Minimize
total_cost: 0.008 Beef_Percentage + 0.013 Chicken_Percentage
Subject To
Fat_Req: 0.1 Beef_Percentage + 0.08 Chicken_Percentage >= 6
Fibre_Req: 0.005 Beef_Percentage + 0.001 Chicken_Percentage <= 2
Percentage_Sum: Beef_Percentage + Chicken_Percentage = 100
Protein_Req: 0.2 Beef_Percentage + 0.1 Chicken_Percentage >= 8
Salt_Req: 0.005 Beef_Percentage + 0.002 Chicken_Percentage <= 0.4
Bounds
 0 <= Beef_Percentage <= 100
 0 <= Chicken_Percentage <= 100
Generals
Beef_Percentage
Chicken_Percentage
End
