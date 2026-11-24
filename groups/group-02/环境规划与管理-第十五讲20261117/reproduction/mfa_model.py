# -*- coding: utf-8 -*-
"""全球人为磷循环五子系统物质流分析（单位：Mt P）。

模型以农产品纯磷数据为锚，并以论文基准值标定化肥、LBS PUE 和累计
磷矿需求。所有桑基连接来自 ``flow_records``，守恒检查直接核算流量，
不再用“总输入减总输出”倒算全系统存量。
"""

import numpy as np
import pandas as pd

import data_loader as dl

# G 为动物产品，M 为活畜；二者作为 LBS 的不同输出，不共同进入居民食物消费。
ANIMAL_FOOD_CATEGORIES = {"G"}
LIVE_ANIMAL_CATEGORIES = {"M"}
ANIMAL_CATEGORIES = ANIMAL_FOOD_CATEGORIES | LIVE_ANIMAL_CATEGORIES


class GlobalPModel:
    """全球人为磷循环 PMS、CIS、ACS、LBS、RCS 五子系统模型。"""

    def __init__(self):
        self.prod = dl.load_product_p()
        self.cropland_area = dl.load_cropland_area()
        self.population = dl.load_population()
        self.rock_p2o5 = dl.load_rock_p2o5()

        self._prod_mt = self.prod.groupby("Year")["P_kt"].sum() / 1e3
        self._crop_mt = (self.prod[~self.prod["Category"].isin(ANIMAL_CATEGORIES)]
                         .groupby("Year")["P_kt"].sum() / 1e3)
        self._animal_mt = (self.prod[self.prod["Category"].isin(ANIMAL_CATEGORIES)]
                           .groupby("Year")["P_kt"].sum() / 1e3)
        self._animal_food_mt = (
            self.prod[self.prod["Category"].isin(ANIMAL_FOOD_CATEGORIES)]
            .groupby("Year")["P_kt"].sum() / 1e3)
        self._live_animals_mt = (
            self.prod[self.prod["Category"].isin(LIVE_ANIMAL_CATEGORIES)]
            .groupby("Year")["P_kt"].sum() / 1e3)

        # 论文标定参数
        self.P_FERT_1961 = 4.9
        self.P_FERT_2022 = 20.5
        self.LBS_PUE = 0.23
        self.FERT_SHARE_ACS = 0.64
        self.ROCK_CUM_1961_2022 = 1153.0

        # 模型假设/校准状态量。负值表示土壤存量释放，而非负的环境汇。
        self.P_ATM_2022 = 1.0
        self.P_SEED_2022 = 0.4
        self.P_ACS_LEGACY_2022 = -14.638828088337199
        self.P_LEACHING_2022 = 3.0
        self.P_MANURE_LOSS_2022 = 4.0
        self.P_CROP_FOOD_2022 = 18.0
        self.P_CROP_FEED_2022 = 20.0
        self.P_SEWAGE_2022 = 5.0
        self.P_WASTE_2022 = 1.5

        self.flows = {}
        self.flow_records = []
        self._calibrate_nonfert_share()

    def _calibrate_nonfert_share(self):
        """由累计磷矿基准标定非化肥用途占比。"""
        fert_cum = self.fertilizer_series().sum()
        self.nonfert_share = float(1.0 - fert_cum / self.ROCK_CUM_1961_2022)

    def fertilizer_series(self):
        """以作物纯磷产出为需求驱动重建 1961–2022 化肥序列。"""
        crop = self._crop_mt.loc[1961:2022]
        ratio = (crop / crop.loc[1961]).replace([np.inf, -np.inf], np.nan).fillna(1.0)
        exponent = np.log(self.P_FERT_2022 / self.P_FERT_1961) / np.log(ratio.loc[2022])
        fert = self.P_FERT_1961 * ratio ** exponent
        fert.loc[1961] = self.P_FERT_1961
        fert.loc[2022] = self.P_FERT_2022
        return fert

    def rock_series(self):
        """重建 1961–2022 磷矿需求序列（Mt P）。"""
        return self.fertilizer_series() / (1.0 - self.nonfert_share)

    def build_2022_flows(self):
        """构建 2022 年流量及唯一的桑基流量台账。"""
        crop_harvest = float(self._crop_mt.loc[2022])
        animal_product = float(self._animal_mt.loc[2022])
        animal_food = float(self._animal_food_mt.loc[2022])
        live_animals = float(self._live_animals_mt.loc[2022])
        rock = float(self.rock_series().loc[2022])
        fert = self.P_FERT_2022
        nonfert = rock - fert

        feed_input = animal_product / self.LBS_PUE
        manure = feed_input - animal_product
        manure_return = (fert * (1.0 / self.FERT_SHARE_ACS - 1.0)
                         - self.P_ATM_2022 - self.P_SEED_2022)

        # 显式闭合项：非作物饲料、牧场还田和消费端未分配用途。
        crop_feed = self.P_CROP_FEED_2022
        other_feed = feed_input - crop_feed
        manure_loss = self.P_MANURE_LOSS_2022
        pasture_manure = manure - manure_return - manure_loss
        crop_other = (crop_harvest - self.P_CROP_FOOD_2022 - crop_feed
                      - self.P_SEED_2022)
        food_input = self.P_CROP_FOOD_2022 + animal_food
        consumer_unallocated = food_input - self.P_SEWAGE_2022 - self.P_WASTE_2022

        named_positive = {
            "非作物饲料": other_feed,
            "牧场粪便": pasture_manure,
            "其他作物用途": crop_other,
            "消费端未分配": consumer_unallocated,
        }
        for name, value in named_positive.items():
            if value < 0:
                raise ValueError(f"{name}闭合项为负（{value:.6f} Mt P），请检查流量假设")

        # 外部输入/输出独立汇总；土壤存量变化使用独立校准状态量。
        total_in = rock + self.P_ATM_2022 + other_feed
        total_out = (nonfert + self.P_LEACHING_2022 + crop_other + live_animals
                     + manure_loss + pasture_manure + self.P_SEWAGE_2022
                     + self.P_WASTE_2022 + consumer_unallocated)

        self.flows = {
            "P_rock": rock,
            "P_atm": self.P_ATM_2022,
            "P_fert": fert,
            "P_nonfert": nonfert,
            "P_seed": self.P_SEED_2022,
            "P_manure_return": manure_return,
            "P_crop_harvest": crop_harvest,
            "P_crop_food": self.P_CROP_FOOD_2022,
            "P_crop_feed": crop_feed,
            "P_crop_other": crop_other,
            "P_leaching": self.P_LEACHING_2022,
            "P_acs_legacy": self.P_ACS_LEGACY_2022,
            "P_feed_input": feed_input,
            "P_other_feed": other_feed,
            "P_animal_product": animal_product,
            "P_animal_food": animal_food,
            "P_live_animals": live_animals,
            "P_manure": manure,
            "P_manure_loss": manure_loss,
            "P_pasture_manure": pasture_manure,
            "P_food_input": food_input,
            "P_sewage": self.P_SEWAGE_2022,
            "P_waste": self.P_WASTE_2022,
            "P_consumer_unallocated": consumer_unallocated,
            "Total_Input": total_in,
            "Total_Output": total_out,
            "Soil_Legacy_P": self.P_ACS_LEGACY_2022,
        }

        records = [
            ("P_rock", "Phosphate_Rock", "Chemical_Industry"),
            ("P_fert", "Chemical_Industry", "Cropland"),
            ("P_nonfert", "Chemical_Industry", "Waterbody"),
            ("P_atm", "Atmosphere", "Cropland"),
            ("P_manure_return", "Livestock", "Cropland"),
            ("P_seed", "Crop_Harvest", "Cropland"),
            ("P_crop_harvest", "Cropland", "Crop_Harvest"),
            ("P_leaching", "Cropland", "Waterbody"),
            ("P_crop_food", "Crop_Harvest", "Consumption"),
            ("P_crop_feed", "Crop_Harvest", "Livestock"),
            ("P_crop_other", "Crop_Harvest", "Landfill"),
            ("P_other_feed", "Other_Feed_Sources", "Livestock"),
            ("P_animal_food", "Livestock", "Consumption"),
            ("P_live_animals", "Livestock", "Live_Animal_Use"),
            ("P_manure_loss", "Livestock", "Waterbody"),
            ("P_pasture_manure", "Livestock", "Pasture"),
            ("P_sewage", "Consumption", "Waterbody"),
            ("P_waste", "Consumption", "Landfill"),
            ("P_consumer_unallocated", "Consumption", "Consumer_Unallocated"),
        ]
        if self.P_ACS_LEGACY_2022 >= 0:
            records.append(("P_acs_legacy", "Cropland", "Soil_Legacy_P"))
        else:
            records.append(("P_acs_legacy", "Soil_Legacy_P", "Cropland"))

        self.flow_records = [
            {"key": key, "source": source, "target": target,
             "value": abs(float(self.flows[key]))}
            for key, source, target in records
        ]
        return self.flows

    @staticmethod
    def _rel_error(total_in, total_out, stock_delta):
        return abs(total_in - total_out - stock_delta) / (total_in + 1e-6)

    def _balance_table(self, flows):
        """从原始流量独立汇总各子系统，而非读取汇总后总量。"""
        f = flows
        rows = [
            ("PMS", f["P_rock"], f["P_rock"], 0.0),
            ("CIS", f["P_rock"], f["P_fert"] + f["P_nonfert"], 0.0),
            ("ACS", f["P_fert"] + f["P_manure_return"] + f["P_atm"] + f["P_seed"],
             f["P_crop_harvest"] + f["P_leaching"], f["P_acs_legacy"]),
            ("LBS", f["P_crop_feed"] + f["P_other_feed"],
             f["P_animal_food"] + f["P_live_animals"] + f["P_manure_return"]
             + f["P_manure_loss"] + f["P_pasture_manure"], 0.0),
            ("RCS", f["P_crop_food"] + f["P_animal_food"],
             f["P_sewage"] + f["P_waste"] + f["P_consumer_unallocated"], 0.0),
            ("全系统", f["P_rock"] + f["P_atm"] + f["P_other_feed"],
             f["P_nonfert"] + f["P_leaching"] + f["P_crop_other"]
             + f["P_live_animals"] + f["P_manure_loss"] + f["P_pasture_manure"]
             + f["P_sewage"] + f["P_waste"] + f["P_consumer_unallocated"],
             f["P_acs_legacy"]),
        ]
        return pd.DataFrame([
            {"子系统": name, "输入_MtP": total_in, "输出_MtP": total_out,
             "存量变化_MtP": stock, "相对误差": self._rel_error(total_in, total_out, stock)}
            for name, total_in, total_out, stock in rows
        ])

    def mass_balance_report(self):
        return self._balance_table(self.flows)

    def verify_mass_balance(self, tolerance=1e-4):
        """验证五个子系统、全系统及派生流量的一致性。"""
        if not self.flows:
            raise RuntimeError("请先调用 build_2022_flows()")
        f = self.flows
        identities = [
            ("饲料输入", f["P_feed_input"], f["P_crop_feed"] + f["P_other_feed"]),
            ("动物输出", f["P_animal_product"], f["P_animal_food"] + f["P_live_animals"]),
            ("粪便分流", f["P_manure"], f["P_manure_return"] + f["P_manure_loss"]
             + f["P_pasture_manure"]),
            ("收获分流", f["P_crop_harvest"], f["P_crop_food"] + f["P_crop_feed"]
             + f["P_crop_other"] + f["P_seed"]),
            ("居民食物输入", f["P_food_input"], f["P_crop_food"] + f["P_animal_food"]),
        ]
        for name, left, right in identities:
            error = abs(left - right) / (abs(left) + 1e-6)
            assert error < tolerance, f"{name}一致性未通过，相对误差: {error:.6e}"

        table = self.mass_balance_report()
        failed = table[table["相对误差"] >= tolerance]
        assert failed.empty, "质量守恒未通过：\n" + failed.to_string(index=False)

        global_in = f["P_rock"] + f["P_atm"] + f["P_other_feed"]
        global_out = (f["P_nonfert"] + f["P_leaching"] + f["P_crop_other"]
                      + f["P_live_animals"] + f["P_manure_loss"] + f["P_pasture_manure"]
                      + f["P_sewage"] + f["P_waste"] + f["P_consumer_unallocated"])
        for name, stored, calculated in [
            ("Total_Input", f["Total_Input"], global_in),
            ("Total_Output", f["Total_Output"], global_out),
            ("Soil_Legacy_P", f["Soil_Legacy_P"], f["P_acs_legacy"]),
        ]:
            assert abs(stored - calculated) / (abs(calculated) + 1e-6) < tolerance, name
        return float(table.loc[table["子系统"] == "全系统", "相对误差"].iloc[0])

    def verify_balance_detection(self, tolerance=1e-4):
        """扰动一条内部流，确认守恒检查并非恒等式。"""
        perturbed = dict(self.flows)
        perturbed["P_fert"] += max(abs(perturbed["P_fert"]) * 0.01, 0.01)
        errors = self._balance_table(perturbed)
        detected = errors.loc[errors["相对误差"] >= tolerance, "子系统"].tolist()
        assert detected, "扰动测试失败：守恒检查无法发现非闭合流"
        return detected

    def sankey_node_balances(self):
        """返回桑基内部过程节点的输入、输出与相对误差。"""
        rows = []
        for node in ["Chemical_Industry", "Cropland", "Crop_Harvest", "Livestock", "Consumption"]:
            incoming = sum(r["value"] for r in self.flow_records if r["target"] == node)
            outgoing = sum(r["value"] for r in self.flow_records if r["source"] == node)
            rows.append({"节点": node, "输入_MtP": incoming, "输出_MtP": outgoing,
                         "相对误差": abs(incoming - outgoing) / (incoming + 1e-6)})
        return pd.DataFrame(rows)

    def sankey_data(self):
        """从统一流量台账返回 Plotly 节点映射。"""
        nodes = [
            "Other_Feed_Sources", "Atmosphere", "Soil_Legacy_P", "Phosphate_Rock",
            "Chemical_Industry", "Cropland", "Crop_Harvest", "Livestock", "Consumption",
            "Waterbody", "Pasture", "Landfill", "Live_Animal_Use", "Consumer_Unallocated",
        ]
        node_map = {name: index for index, name in enumerate(nodes)}
        sources = [node_map[r["source"]] for r in self.flow_records]
        targets = [node_map[r["target"]] for r in self.flow_records]
        values = [r["value"] for r in self.flow_records]
        return nodes, sources, targets, values

    def benchmarks(self):
        """返回文献标定、数据计算和外部核验分组对照表。"""
        f = self.flows
        fert_ratio = f["P_fert"] / (f["P_fert"] + f["P_manure_return"]
                                    + f["P_atm"] + f["P_seed"])
        lbs_pue = f["P_animal_product"] / f["P_feed_input"]
        usgs_2021 = float(self.rock_p2o5.get(2021, np.nan)) * dl.T_P2O5_TO_P / 1e6
        rows = [
            ("1961 矿物磷肥 (Mt P)", self.P_FERT_1961, 4.9, "文献标定", "端点约束"),
            ("2022 矿物磷肥 (Mt P)", f["P_fert"], 20.5, "文献标定", "端点约束"),
            ("1961–2022 累计磷矿 (Mt P)", self.rock_series().sum(), 1153.0,
             "文献标定", "反解非化肥用途占比"),
            ("2022 化肥占农田输入比例", fert_ratio, 0.64, "文献标定", "论文为 >64%"),
            ("LBS 磷利用效率 (PUE)", lbs_pue, 0.23, "文献标定", "历史均值代理"),
            ("2022 作物纯磷产出 (Mt P)", f["P_crop_harvest"], None, "数据计算", "排除 G/M"),
            ("2022 动物产品纯磷 (Mt P)", f["P_animal_food"], None, "数据计算", "仅 G"),
            ("2022 活畜纯磷 (Mt P)", f["P_live_animals"], None, "数据计算", "仅 M，单列避免混入食物"),
            ("2022 农田土壤存量变化 (Mt P)", f["P_acs_legacy"], None,
             "模型校准", "负值表示土壤存量释放"),
            ("2021 磷矿需求/USGS 对照 (Mt P)", float(self.rock_series().loc[2021]), usgs_2021,
             "外部数据核验", "USGS 表国家覆盖不完整，不作零偏差声明"),
        ]
        table = pd.DataFrame(rows, columns=["指标", "复现值", "文献或外部对照值", "数据性质", "备注"])
        table["相对偏差_%"] = ((table["复现值"] - table["文献或外部对照值"])
                               / table["文献或外部对照值"] * 100)
        return table


if __name__ == "__main__":
    model = GlobalPModel()
    flows = model.build_2022_flows()
    print("2022 年全球人为磷循环 MFA 核算 (Mt P)")
    for key, value in flows.items():
        print(f"  {key:26s} = {value:10.4f}")
    model.verify_mass_balance()
    print(model.mass_balance_report().to_string(index=False))
    print("扰动检测子系统:", model.verify_balance_detection())
    print(model.benchmarks().to_string(index=False))
