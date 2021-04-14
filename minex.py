import pandas as pd
from pulp import *


class InventoryModel():
  """class used to define and construct the inventory linear program
     data_path: the file path of the data containing the orders
     prodcut_col: string of the column's header containing the product (group) id
     time_col: string of the column's header containing the date of the order
     loc_col: string of the column's header containing the location of the order
     qty_col: string of the column's header containing the quantity of the order
  """

  def __init__(self, data_path, product_col, time_col, loc_col, qty_col):
    self.product_col = product_col
    self.time_col = time_col
    self.loc_col = loc_col
    self.raw_data = pd.read_csv(data_path,
                                usecols=[product_col,
                                         time_col,
                                         loc_col,
                                         qty_col])
    self.raw_data = self.raw_data.groupby([product_col, time_col, loc_col]).sum()
    print(self.raw_data)
    self.inv_model = pulp.LpProblem("Inventory_Optimization",
                                    LpMinimize)  # creates an object of an LpProblem (PuLP) to which we will assign variables, constraints and objective function

  def define_indices(self):
    ''' Returns the unique values for indices from the input data
    Required keywords argument:
    new_time_col: string of the aggregation basis for time (e.g. "week", "month",...)
    '''
    self.prod_id = self.raw_data.index.get_level_values(
            self.product_col).unique().tolist()
    self.time_id = self.raw_data.index.get_level_values(
            self.time_col).unique().tolist()
    self.loc_id = self.raw_data.index.get_level_values(
            self.loc_col).unique().tolist()

  def define_paramaters(self, loc_data_path):
    ''' Returns a dataframe of the paramaters required for the model
    loc_data_path: string of the path to the location data
    demand_data_path: string of the path of pre-computed statistics of the demand
    '''
    self.loc_data = pd.read_csv(loc_data_path,
                                index_col=[0])

  def define_variables(self):
    '''Defines the variable and their nature whcih are then added to the model
    '''
    self.inv_level = pulp.LpVariable.dicts("inventory level",
                                           (self.prod_id,
                                            self.loc_id,
                                            self.time_id),
                                           lowBound=0)

  def define_objective(self):
    ''' Defines the objective funciton
    '''
    holding_costs = pulp.lpSum((self.inv_level[i][w][t] * self.loc_data.loc[w, "Hold. Costs"]
                                for i in self.prod_id
                                for w in self.loc_id
                                for t in self.time_id))

    self.inv_model += holding_costs

  def define_constraints(self):
    '''Defines the constraints to be added to the model
    '''
    for w in self.loc_id:
      for ind, t in enumerate(self.time_id):
        for i in self.prod_id:
          try:

            self.inv_model += lpSum(
                self.raw_data.loc[(t, i, w)] - self.inv_level[i][w][t]) == 0

          except KeyError:
            continue
          self.inv_model += lpSum((self.inv_level[i][w][t]
                                   for i in self.prod_id)) <= self.loc_data.loc[w, "Hold. Cap."]

  def build_model(self):
    ''' calls all the required function to initialize, solve and export the model
    '''
    self.define_indices()
    self.define_variables()
    self.define_paramaters(loc_data_path="loc_data.csv")
    self.define_objective()
    self.define_constraints()
    solver = CPLEX_PY()
    self.inv_model.solve(solver)


I = InventoryModel(data_path="input.csv",
                   product_col="varvol_cluster",
                   time_col="week",
                   loc_col="sh_OriginLocationMasterLocation",
                   qty_col="Pallets")
I.build_model()
