import pandas as pd
import numpy as np


class ACSPModel:
    """Agricultural Cultivation System (ACS) Phosphorus Flow Model, parameters input via DataFrames"""

    def __init__(self, crop_params_df, system_params_df):
        """
        Initialize the model
        :param crop_params_df: Crop-level parameters DataFrame, containing yield, coefficients, etc. for each crop
        :param system_params_df: System-level parameters DataFrame, containing global parameters like cultivated area, ratios, etc.
        """
        self.crop_params = crop_params_df
        self.system_params = system_params_df

    def TP_crop_product(self):
        """Calculate total phosphorus of crops"""
        return np.sum(self.crop_params['M_i'] * self.crop_params['mi'])

    def crop_uptake_p(self):
        """Calculate total phosphorus uptake by crops (P_crops_uptake_P)
        Formula: sum(Q_crop_i × κ_ui)"""
        return np.sum(self.crop_params['Q_crop_i'] * self.crop_params['κ_ui'])

    def crop_harvest_p(self):
        """Calculate phosphorus content in crop harvest (P_crops_harvest_P)
        Formula: sum(Q_crop_i × κ_hi)"""
        return np.sum(self.crop_params['Q_crop_i'] * self.crop_params['κ_hi'])

    def crop_residue_p(self):
        """Calculate phosphorus content in crop residues (P_crops_residue_P)
        Formula: P_crops_uptake_P - P_crops_harvest_P"""
        return self.crop_uptake_p() - self.crop_harvest_p()

    def crop_food_p(self):
        """Calculate phosphorus content used for food (P_crops_food)
        Formula: sum(Q_crop_i × κ_hi × κ_harvest_food_i)"""
        return np.sum(
            self.crop_params['Q_crop_i'] *
            self.crop_params['κ_hi'] *
            self.crop_params['κ_harvest_food_i']
        )

    def crop_feed_p(self):
        """Calculate phosphorus content used for feed (P_crops_feed)
        Formula: sum(Q_crop_i × κ_hi × κ_harvest_feed_i)"""
        return np.sum(
            self.crop_params['Q_crop_i'] *
            self.crop_params['κ_hi'] *
            self.crop_params['κ_harvest_feed_i']
        )

    def crop_other_products_p(self):
        """
        Calculate phosphorus content in crop harvest used for other products ($P_{crops\_other\_products}$).
        Formula: sum(Q_crop_i × κ_hi × κ_harvest_other_products_i)
        """
        return np.sum(
            self.crop_params['Q_crop_i'] *
            self.crop_params['κ_hi'] *
            self.crop_params['κ_harvest_other_products_i']
        )

    def crop_waste_p(self):
        """
        Calculate phosphorus content in crop harvest that becomes waste ($P_{crops\_waste}$).
        Formula: sum(Q_crop_i × κ_hi × κ_harvest_waste_i)
        """
        return np.sum(
            self.crop_params['Q_crop_i'] *
            self.crop_params['κ_hi'] *
            self.crop_params['κ_harvest_waste_i']
        )

    def reuse_organic_fertilizer_p(self):
        """Calculate phosphorus content in residues reused as organic fertilizer (P_reuse_crops_organic_fertilizer)
        Formula: P_crops_residue_P × β1"""
        beta1 = self.system_params.loc['β1', 'value']
        return self.crop_residue_p() * beta1

    def reuse_crops_feed_p(self):
        """
        Calculate reuse of crop residue as feed phosphorus (P_reuse_crops_feed).
        Formula: P_crops_harvest_P × β2
        """
        beta2 = self.system_params.loc['β2', 'value']
        return self.crop_harvest_p() * beta2

    def drainage_leaching_p(self):
        """Calculate phosphorus loss through drainage and leaching (P_ACS→SW)
        Formula: P_FD + P_Leaching (where P_FD = S_cropland × κ_drainige, P_Leaching = S_cropland × κ_leaching)"""
        s_cropland = self.system_params.loc['S_cropland', 'value']
        kappa_drainage = self.system_params.loc['κ_drainige', 'value']
        kappa_leaching = self.system_params.loc['κ_leaching', 'value']
        return s_cropland * kappa_drainage + s_cropland * kappa_leaching

    # The P_flow calculation process for cross-validation in ACS

    def atmospheric_deposition_p(self):
        """Calculate total phosphorus from atmospheric deposition (P_AD)
        Formula: S_cropland × s"""
        s_cropland = self.system_params.loc['S_cropland', 'value']
        s = self.system_params.loc['s', 'value']
        return s_cropland * s

    def seed_p(self):
        """
        Calculate total phosphorus content of seeds (P_Seed).
        Formula: sum(S_m × K_m) for m = 1 to 8
        """
        # 假设作物参数DataFrame里有'S_m'和'K_m'列，且索引对应m=1到8的作物
        return np.sum(self.crop_params['S_m'] * self.crop_params['K_m'])

    def straw_p(self):
        """
        Calculate TP content of crop straw (P_straw).
        Formula: sum(E_i × e_i × f_i) for i = 1 to 10
        """
        return np.sum(
            self.crop_params['E_i'] *
            self.crop_params['e_i'] *
            self.crop_params['f_i']
        )

    def returned_snpk_p(self):
        """
        Calculate TP content of returned straw (P_SNRK).
        Formula: sum(E_i × e_i × g_i × F_i) for i = 1 to 10
        Where P_SNRK is the TP content of returned straw;
        """
        return np.sum(
            self.crop_params['E_i'] *
            self.crop_params['e_i'] *
            self.crop_params['g_i'] *
            self.crop_params['F_i']
        )

    def straw_waste_p(self):
        """
        Calculate P content of straw waste (P_SW).
        Formula: P_straw - P_SNRK
        """
        return self.straw_p() - self.returned_snpk_p()

    def acs_non_cropland_p(self):
        """
        Calculate phosphorus in ACS non-cropland (P_ACS-Non_cropland).
        Formula: P_ACS-Non_cropland = P_SW
        Where P_ACS-Non_cropland is phosphorus in ACS non-cropland;
        P_SW is the P content of straw waste.
        """
        return self.straw_waste_p()

    def SD_p(self):
        """
        Calculate other phosphorus inputs (P_SD).
        Formula: (P_Fertilizer + P_human + P_animal) × h
        """
        p_fertilizer = self.system_params.loc['P_Fertilizer', 'value']
        p_human = self.system_params.loc['P_human', 'value']
        p_animal = self.system_params.loc['P_animal', 'value']
        h = self.system_params.loc['h', 'value']
        return (p_fertilizer + p_human + p_animal) * h

    def acs_to_lbs_p(self):
        """
        Calculate the amount of P in the agricultural product as feed grain (P_ACS→LBS).
        Formula: sum(Q_i^crop × m_i × n_i) for i = 1 to 6
        """
        # 假设作物参数DataFrame里有'Q_i^crop'（列名可根据实际调整，这里用'Q_crop_i'示例 ）、'm_i'、'n_i'列，且i对应1到6种作物
        return np.sum(
            self.crop_params['Q_crop_i'] *
            self.crop_params['m_i'] *
            self.crop_params['n_i']
        )


# Example: Define parameter DataFrame structure
if __name__ == "__main__":
    # 1. Example of crop-level parameters (each row represents a crop)
    crop_params_df = pd.read_csv('excel file path')  # 替换为实际文件路径，需包含对应列（如Q_crop_i、m_i、n_i等）
    # 2. Example of system-level parameters (index is parameter name, value column is parameter value)
    system_params_df = pd.read_csv(
        'excel file path'  # 替换为实际文件路径，需包含对应参数（如P_Fertilizer、P_human等）
    )

    # 3. Model calculation and result output
    model = ACSPModel(crop_params_df, system_params_df)
    print(f"Total phosphorus content of crop products: {model.TP_crop_product():.4f}")
    print(f"Total phosphorus uptake by crops: {model.crop_uptake_p():.4f}")
    print(f"Phosphorus content in crop harvest: {model.crop_harvest_p():.4f}")
    print(f"Phosphorus content used for food: {model.crop_food_p():.4f}")
    print(f"Phosphorus content used for feed: {model.crop_feed_p():.4f}")
    print(f"Reuse of crop residue as feed phosphorus: {model.reuse_crops_feed_p():.4f}")
    print(f"Phosphorus in crop harvest for other products: {model.crop_other_products_p():.4f}")
    print(f"Phosphorus in crop harvest as waste: {model.crop_waste_p():.4f}")
    print(f"Total phosphorus from atmospheric deposition: {model.atmospheric_deposition_p():.4f}")
    print(f"Phosphorus loss from ACS to surface water (P_ACS→SW): {model.drainage_leaching_p():.4f}")
    print(f"Total phosphorus content of seeds: {model.seed_p():.4f}")
    print(f"TP content of crop straw: {model.straw_p():.4f}")
    print(f"TP content of returned straw: {model.returned_snpk_p():.4f}")
    print(f"P content of straw waste: {model.straw_waste_p():.4f}")
    print(f"Phosphorus in ACS non-cropland: {model.acs_non_cropland_p():.4f}")
    print(f"Amount of P deposited in the soil: {model.SD_p():.4f}")
    print(f"Amount of P in agricultural product as feed grain (P_ACS→LBS): {model.acs_to_lbs_p():.4f}")
