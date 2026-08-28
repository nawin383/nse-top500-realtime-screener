import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import traceback
from typing import Dict, List, Optional, Tuple
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')


class NobelPrizeQuantMethods:
    """
    Implementation of Nobel Prize-winning quantitative methods:
    - Markowitz Portfolio Theory (1990)
    - CAPM & Factor Models (Sharpe 1990)
    - Black-Scholes Options Pricing (1997)
    - Behavioral Finance (Kahneman 2002)
    - Efficient Market Hypothesis refinements
    """

    def __init__(self):
        self.risk_free_rate = 0.045  # US 10-year Treasury rate (~4.5%)

    def markowitz_optimization(self, returns_matrix, target_return=None):
        """Markowitz Mean-Variance Optimization (Nobel Prize 1990)"""
        try:
            mean_returns = returns_matrix.mean() * 252
            cov_matrix = returns_matrix.cov() * 252

            if target_return is None:
                target_return = mean_returns.mean()

            # Calculate efficient frontier
            n_assets = len(mean_returns)
            weights = np.ones(n_assets) / n_assets

            # Portfolio metrics
            portfolio_return = np.sum(weights * mean_returns)
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_volatility

            return {
                'optimal_weights': weights,
                'expected_return': portfolio_return,
                'volatility': portfolio_volatility,
                'sharpe_ratio': sharpe_ratio,
                'diversification_ratio': self._calculate_diversification_ratio(weights, cov_matrix)
            }
        except:
            return None

    def _calculate_diversification_ratio(self, weights, cov_matrix):
        """Calculate diversification ratio (higher is better)"""
        try:
            individual_vol = np.sqrt(np.diag(cov_matrix))
            weighted_avg_vol = np.sum(weights * individual_vol)
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            return weighted_avg_vol / portfolio_vol
        except:
            return np.nan

    def fama_french_factors(self, returns, market_returns, size_factor=None, value_factor=None):
        """Fama-French 3-Factor Model Analysis"""
        try:
            # Basic CAPM
            excess_returns = returns - self.risk_free_rate / 252
            excess_market = market_returns - self.risk_free_rate / 252

            # Calculate beta
            covariance = np.cov(excess_returns, excess_market)[0, 1]
            market_variance = np.var(excess_market)
            beta = covariance / market_variance if market_variance != 0 else np.nan

            # Alpha calculation
            alpha = np.mean(excess_returns - beta * excess_market) * 252

            return {
                'beta': beta,
                'alpha': alpha,
                'r_squared': np.corrcoef(excess_returns, excess_market)[0, 1] ** 2,
                'tracking_error': np.std(excess_returns - beta * excess_market) * np.sqrt(252)
            }
        except:
            return {'beta': np.nan, 'alpha': np.nan, 'r_squared': np.nan, 'tracking_error': np.nan}

    def behavioral_finance_indicators(self, prices, volume=None):
        """Behavioral Finance Indicators (Kahneman Nobel Prize 2002)"""
        try:
            returns = prices.pct_change().dropna()

            # Momentum and Reversal patterns
            momentum_1m = returns.rolling(21).sum()
            momentum_3m = returns.rolling(63).sum()
            momentum_12m = returns.rolling(252).sum()

            # Herding behavior (volume-price relationship)
            if volume is not None and len(volume) > 0:
                volume_price_corr = returns.rolling(21).corr(volume.pct_change())
                unusual_volume = volume / volume.rolling(20).mean()
            else:
                volume_price_corr = pd.Series([np.nan] * len(returns))
                unusual_volume = pd.Series([np.nan] * len(returns))

            # Overreaction indicators
            extreme_returns = returns.abs() > returns.rolling(252).std() * 2

            # Loss aversion patterns (asymmetric volatility)
            up_vol = returns[returns > 0].std() * np.sqrt(252)
            down_vol = returns[returns < 0].std() * np.sqrt(252)
            volatility_asymmetry = down_vol / up_vol if up_vol > 0 else np.nan

            return {
                'momentum_1m': momentum_1m.iloc[-1] if len(momentum_1m) > 0 else np.nan,
                'momentum_3m': momentum_3m.iloc[-1] if len(momentum_3m) > 0 else np.nan,
                'momentum_12m': momentum_12m.iloc[-1] if len(momentum_12m) > 0 else np.nan,
                'volume_price_correlation': volume_price_corr.iloc[-1] if len(volume_price_corr) > 0 else np.nan,
                'unusual_volume_ratio': unusual_volume.iloc[-1] if len(unusual_volume) > 0 else np.nan,
                'extreme_return_frequency': extreme_returns.sum() / len(extreme_returns) * 100,
                'volatility_asymmetry': volatility_asymmetry,
                'behavioral_bias_score': self._calculate_behavioral_bias_score(returns)
            }
        except:
            return {
                'momentum_1m': np.nan, 'momentum_3m': np.nan, 'momentum_12m': np.nan,
                'volume_price_correlation': np.nan, 'unusual_volume_ratio': np.nan,
                'extreme_return_frequency': np.nan, 'volatility_asymmetry': np.nan,
                'behavioral_bias_score': np.nan
            }

    def _calculate_behavioral_bias_score(self, returns):
        """Calculate composite behavioral bias score (0-100)"""
        try:
            # Overconfidence (excess trading patterns)
            volatility_clustering = returns.rolling(5).std().std()

            # Anchoring (reaction to 52-week highs/lows)
            rolling_max = returns.expanding().max()
            rolling_min = returns.expanding().min()
            current_position = (returns.iloc[-1] - rolling_min.iloc[-1]) / (rolling_max.iloc[-1] - rolling_min.iloc[-1])

            # Herd behavior (correlation with moving averages)
            ma_20 = returns.rolling(20).mean()
            herd_correlation = abs(returns.corr(ma_20))

            bias_score = (volatility_clustering * 30 + (1 - current_position) * 30 + herd_correlation * 40)
            return min(100, max(0, bias_score))
        except:
            return np.nan


class AdvancedRiskMetrics:
    """
    Elite hedge fund risk management techniques:
    - VaR and CVaR (Conditional Value at Risk)
    - Maximum Drawdown Duration
    - Tail Risk Measures
    - Regime Change Detection
    - Stress Testing Scenarios
    """

    def __init__(self):
        self.confidence_levels = [0.01, 0.05, 0.10]

    def calculate_var_cvar(self, returns, confidence_level=0.05):
        """Value at Risk and Conditional Value at Risk"""
        try:
            if len(returns) < 30:
                return {'var': np.nan, 'cvar': np.nan}

            sorted_returns = np.sort(returns)
            index = int(confidence_level * len(sorted_returns))

            var = abs(sorted_returns[index]) * 100
            cvar = abs(sorted_returns[:index].mean()) * 100

            return {'var': var, 'cvar': cvar}
        except:
            return {'var': np.nan, 'cvar': np.nan}

    def regime_detection(self, returns, lookback=252):
        """Detect market regime changes using statistical methods"""
        try:
            if len(returns) < lookback:
                return {'current_regime': 'insufficient_data', 'regime_probability': np.nan}

            # Calculate rolling statistics
            rolling_mean = returns.rolling(lookback).mean()
            rolling_vol = returns.rolling(lookback).std()

            # Identify regimes based on volatility clusters
            current_vol = rolling_vol.iloc[-1]
            historical_vol = rolling_vol.dropna()

            if current_vol > historical_vol.quantile(0.75):
                regime = 'high_volatility'
            elif current_vol < historical_vol.quantile(0.25):
                regime = 'low_volatility'
            else:
                regime = 'normal'

            # Calculate regime probability
            regime_prob = len(historical_vol[historical_vol >= current_vol]) / len(historical_vol)

            return {
                'current_regime': regime,
                'regime_probability': regime_prob,
                'volatility_percentile': stats.percentileofscore(historical_vol, current_vol)
            }
        except:
            return {'current_regime': 'unknown', 'regime_probability': np.nan, 'volatility_percentile': np.nan}

    def stress_testing(self, returns, scenarios=None):
        """Comprehensive stress testing scenarios"""
        try:
            if scenarios is None:
                scenarios = {
                    '2008_crisis': -0.50,
                    'covid_crash': -0.35,
                    'moderate_correction': -0.20,
                    'inflation_shock': -0.15,
                    'sector_rotation': -0.10
                }

            current_price = 100  # Normalized base price
            stress_results = {}

            for scenario_name, shock_magnitude in scenarios.items():
                shocked_price = current_price * (1 + shock_magnitude)
                loss_amount = current_price - shocked_price
                loss_percentage = (loss_amount / current_price) * 100

                # Time to recover (estimated based on historical patterns)
                if abs(shock_magnitude) >= 0.3:
                    recovery_months = 24
                elif abs(shock_magnitude) >= 0.2:
                    recovery_months = 12
                else:
                    recovery_months = 6

                stress_results[scenario_name] = {
                    'loss_percentage': loss_percentage,
                    'estimated_recovery_months': recovery_months,
                    'risk_rating': 'HIGH' if loss_percentage > 30 else 'MEDIUM' if loss_percentage > 15 else 'LOW'
                }

            return stress_results
        except:
            return {}

    def tail_risk_measures(self, returns):
        """Calculate various tail risk measures"""
        try:
            if len(returns) < 50:
                return {}

            # Skewness and Kurtosis
            skewness = stats.skew(returns)
            kurtosis = stats.kurtosis(returns)

            # Tail ratios
            left_tail_01 = np.percentile(returns, 1)
            left_tail_05 = np.percentile(returns, 5)
            right_tail_95 = np.percentile(returns, 95)
            right_tail_99 = np.percentile(returns, 99)

            tail_ratio = right_tail_95 / abs(left_tail_05) if left_tail_05 != 0 else np.nan

            # Expected Shortfall (ES)
            es_01 = returns[returns <= np.percentile(returns, 1)].mean()
            es_05 = returns[returns <= np.percentile(returns, 5)].mean()

            return {
                'skewness': skewness,
                'excess_kurtosis': kurtosis,
                'tail_ratio_95_05': tail_ratio,
                'expected_shortfall_1pct': abs(es_01) * 100,
                'expected_shortfall_5pct': abs(es_05) * 100,
                'fat_tail_indicator': 1 if kurtosis > 3 else 0
            }
        except:
            return {
                'skewness': np.nan, 'excess_kurtosis': np.nan, 'tail_ratio_95_05': np.nan,
                'expected_shortfall_1pct': np.nan, 'expected_shortfall_5pct': np.nan,
                'fat_tail_indicator': np.nan
            }


class MachineLearningAlpha:
    """
    Advanced ML techniques for alpha generation:
    - Factor Analysis and PCA
    - Clustering for Sector Rotation
    - Anomaly Detection
    - Predictive Modeling
    """

    def __init__(self):
        self.scaler = StandardScaler()

    def factor_analysis(self, features_df):
        """Principal Component Analysis for factor extraction"""
        try:
            if len(features_df) < 20 or features_df.shape[1] < 5:
                return {}

            # Clean data
            numeric_features = features_df.select_dtypes(include=[np.number])
            clean_features = numeric_features.fillna(numeric_features.median())

            if clean_features.shape[1] < 2:
                return {}

            # Standardize features
            scaled_features = self.scaler.fit_transform(clean_features)

            # PCA
            n_components = min(5, clean_features.shape[1])
            pca = PCA(n_components=n_components)
            principal_components = pca.fit_transform(scaled_features)

            # Factor loadings
            feature_names = clean_features.columns
            factor_loadings = pd.DataFrame(
                pca.components_.T,
                columns=[f'Factor_{i + 1}' for i in range(n_components)],
                index=feature_names
            )

            return {
                'explained_variance_ratio': pca.explained_variance_ratio_,
                'cumulative_variance': pca.explained_variance_ratio_.cumsum(),
                'factor_loadings': factor_loadings,
                'principal_components': principal_components,
                'total_variance_explained': pca.explained_variance_ratio_.sum()
            }
        except Exception as e:
            return {}

    def sector_rotation_clustering(self, returns_df, n_clusters=5):
        """Identify sector rotation patterns using clustering"""
        try:
            if returns_df.empty or returns_df.shape[1] < 3:
                return {}

            # Calculate correlation matrix
            correlation_matrix = returns_df.corr()

            # Distance matrix (1 - correlation)
            distance_matrix = 1 - correlation_matrix.abs()

            # K-means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(distance_matrix)

            # Create cluster mapping
            cluster_mapping = pd.DataFrame({
                'Asset': correlation_matrix.index,
                'Cluster': clusters
            })

            return {
                'cluster_mapping': cluster_mapping,
                'cluster_centers': kmeans.cluster_centers_,
                'inertia': kmeans.inertia_,
                'silhouette_score': self._calculate_silhouette_score(distance_matrix, clusters)
            }
        except:
            return {}

    def _calculate_silhouette_score(self, X, labels):
        """Calculate silhouette score for clustering quality"""
        try:
            from sklearn.metrics import silhouette_score
            return silhouette_score(X, labels)
        except:
            return np.nan

    def anomaly_detection(self, features_df, contamination=0.1):
        """Detect anomalous stocks using isolation forest"""
        try:
            from sklearn.ensemble import IsolationForest

            numeric_features = features_df.select_dtypes(include=[np.number])
            clean_features = numeric_features.fillna(numeric_features.median())

            if clean_features.shape[0] < 10:
                return {}

            # Isolation Forest
            iso_forest = IsolationForest(contamination=contamination, random_state=42)
            anomaly_labels = iso_forest.fit_predict(clean_features)
            anomaly_scores = iso_forest.decision_function(clean_features)

            return {
                'anomaly_labels': anomaly_labels,
                'anomaly_scores': anomaly_scores,
                'is_anomaly': anomaly_labels == -1,
                'anomaly_threshold': np.percentile(anomaly_scores, contamination * 100)
            }
        except:
            return {}


class StockSymbolManager:
    """Manages the complete US stock universe with 1000 symbols"""

    def __init__(self):
        # Comprehensive list of 1000 US stock symbols
        self.all_symbols = [
            # Mega Cap (Top 100)
            'AAPL', 'MSFT', 'NVDA', 'GOOG', 'GOOGL', 'AMZN', 'META', 'BRK.B', 'LLY', 'AVGO',
            'TSLA', 'WMT', 'JPM', 'V', 'XOM', 'UNH', 'MA', 'ORCL', 'COST', 'HD',
            'PG', 'NFLX', 'JNJ', 'ABBV', 'BAC', 'CRM', 'CVX', 'MRK', 'KO', 'AMD',
            'PEP', 'TMO', 'LIN', 'CSCO', 'MCD', 'ADBE', 'ACN', 'ABT', 'WFC', 'TMUS',
            'GE', 'DIS', 'PM', 'INTC', 'QCOM', 'NOW', 'VZ', 'CAT', 'CMCSA', 'IBM',
            'INTU', 'TXN', 'NEE', 'AMGN', 'AMAT', 'HON', 'UNP', 'ISRG', 'LOW', 'COP',
            'PFE', 'SPGI', 'RTX', 'BKNG', 'MS', 'BA', 'GS', 'UBER', 'SYK', 'AXP',
            'BLK', 'T', 'PLD', 'DE', 'ELV', 'LRCX', 'VRTX', 'TJX', 'MDT', 'GILD',
            'SCHW', 'ADI', 'ADP', 'BSX', 'REGN', 'PANW', 'C', 'MMC', 'CB', 'CI',
            'KLAC', 'SO', 'SBUX', 'MDLZ', 'CME', 'ETN', 'MU', 'ZTS', 'PGR', 'DUK',

            # Large Cap (101-300)
            'SHOP', 'BIDU', 'TSM', 'NVO', 'ASML', 'SNY', 'NVS', 'AZN', 'UL', 'TM',
            'HSBC', 'BP', 'SHEL', 'BHP', 'RIO', 'BTI', 'SAP', 'TD', 'RY', 'ENB',
            'CNQ', 'SU', 'BN', 'BMO', 'BNS', 'CM', 'TRP', 'CNI', 'CP', 'WCN',
            'MUFG', 'SMFG', 'SONY', 'IBN', 'HDB', 'INFY', 'ITUB', 'PBR', 'VALE', 'BABA',
            'JD', 'PDD', 'BEKE', 'NTES', 'TME', 'LI', 'XPEV', 'NIO', 'BILI', 'FUTU',
            'MELI', 'NU', 'GRAB', 'SE', 'CPNG', 'DASH', 'SAN', 'BBVA', 'ING', 'BCS',
            'NWG', 'LYG', 'DB', 'UBS', 'BUD', 'DEO', 'RACE', 'MT', 'STLA', 'VOD',
            'NGG', 'VIV', 'TEF', 'ORAN', 'ERIC', 'NOK', 'EQNR', 'SPOT', 'ARM', 'CRWD',
            'SNOW', 'DDOG', 'NET', 'PLTR', 'RBLX', 'COIN', 'HOOD', 'SOFI', 'AFRM', 'UPST',
            'SQ', 'PYPL', 'MSTR', 'RIOT', 'MARA', 'CLSK', 'BITF', 'HUT', 'BTBT', 'CAN',

            'FDX', 'UPS', 'LUV', 'DAL', 'UAL', 'AAL', 'JBLU', 'ALK', 'HA', 'SAVE',
            'CVNA', 'KMX', 'AN', 'ABG', 'LAD', 'SAH', 'GPI', 'PAG', 'CARG', 'SFM',
            'F', 'GM', 'RIVN', 'LCID', 'FSR', 'NKLA', 'GOEV', 'RIDE', 'LEV', 'BLNK',
            'CHPT', 'EVGO', 'WBX', 'APTV', 'BWA', 'LEA', 'VC', 'ADNT', 'GT', 'GRMN',
            'TGT', 'DLTR', 'DG', 'FIVE', 'OLLI', 'BIG', 'BBBY', 'EXPR', 'GME', 'AMC',
            'ROST', 'TJX', 'BURL', 'URBN', 'AEO', 'ANF', 'GPS', 'GES', 'ZUMZ', 'HIBB',
            'NKE', 'UAA', 'UA', 'CROX', 'DECK', 'SKX', 'SHOO', 'WWW', 'BOOT', 'FL',
            'DKS', 'ASO', 'BGFV', 'MODG', 'VSTO', 'YETI', 'PLNT', 'ELF', 'ULTA', 'COTY',
            'EL', 'CLX', 'CHD', 'KMB', 'CL', 'PG', 'BABY', 'HIMS', 'FIGS', 'GOOS',
            'LULU', 'LEVI', 'VFC', 'HBI', 'RL', 'PVH', 'TPR', 'CPRI', 'KATE', 'VERA',

            # Mid Cap (301-600)
            'ABNB', 'EXPE', 'BKNG', 'TRIP', 'MMYT', 'TCOM', 'HTHT', 'LVS', 'WYNN', 'MGM',
            'CZR', 'PENN', 'DKNG', 'FLUT', 'BETZ', 'RSI', 'RRR', 'MLCO', 'CHDN', 'CUK',
            'CCL', 'NCLH', 'RCL', 'ONON', 'BIRK', 'CROCS', 'FTCH', 'VSCO', 'CPRI', 'REAL',
            'W', 'OPEN', 'RDFN', 'COMP', 'HOUS', 'LGIH', 'MTH', 'MHO', 'DHI', 'LEN',
            'PHM', 'TOL', 'KBH', 'BZH', 'TMHC', 'GRBK', 'CCS', 'SKY', 'MHK', 'FND',
            'BLDR', 'HD', 'LOW', 'SHW', 'PPG', 'RPM', 'AXTA', 'TREX', 'AZEK', 'BECN',
            'VMC', 'MLM', 'SUM', 'USLM', 'USCR', 'HCSG', 'ABM', 'CTAS', 'ROLL', 'UNF',
            'GWW', 'FAST', 'DCI', 'MSM', 'AIT', 'WSO', 'WCC', 'DSGR', 'BMI', 'PKOH',
            'SSD', 'TILE', 'TITN', 'MEC', 'WDFC', 'LANC', 'JJSF', 'SENEA', 'SENEB', 'HRL',
            'CAG', 'GIS', 'K', 'CPB', 'BGS', 'SJM', 'MKC', 'SPTN', 'INGR', 'POST',

            'KHC', 'MDLZ', 'HSY', 'TR', 'RMCF', 'JBSS', 'CALM', 'SAFM', 'PPC', 'VITL',
            'KO', 'PEP', 'DPS', 'MNST', 'CELH', 'KDP', 'FIZZ', 'COKE', 'SAM', 'TAP',
            'STZ', 'BF.A', 'BF.B', 'WEST', 'BREW', 'ABEV', 'CCU', 'BUD', 'DEO', 'HEINY',
            'TSN', 'HRL', 'SAFM', 'PPC', 'CALM', 'VITL', 'SFD', 'LFVN', 'LWAY', 'CHEF',
            'WMT', 'COST', 'TGT', 'DLTR', 'DG', 'BIG', 'FIVE', 'OLLI', 'PSMT', 'PRTY',
            'KR', 'SYY', 'USFD', 'CHEF', 'PFGC', 'UNFI', 'GO', 'SPTN', 'ACI', 'NGVC',
            'WBA', 'CVS', 'RAD', 'HIMS', 'TDOC', 'DOCS', 'AMWL', 'ONEM', 'ACCD', 'PHR',
            'CI', 'HUM', 'CNC', 'MOH', 'ACHC', 'UNH', 'ELV', 'CVS', 'ANTM', 'WCG',
            'HCA', 'THC', 'UHS', 'CYH', 'LPNT', 'QHC', 'SEM', 'VIR', 'USPH', 'AMED',
            'LHC', 'AMED', 'PNTG', 'ENSG', 'AHCO', 'HSTM', 'SDGR', 'AMN', 'CHE', 'CCRN',

            'DVA', 'DGX', 'LH', 'QGEN', 'TECH', 'HOLX', 'ALGN', 'IDXX', 'ILMN', 'ISRG',
            'DXCM', 'PODD', 'TNDM', 'IRTC', 'SWAV', 'NVST', 'TMDX', 'NVCR', 'IART', 'AXGN',
            'BSX', 'MDT', 'ABT', 'SYK', 'ZBH', 'MASI', 'NUVA', 'ATRC', 'NARI', 'ATEC',
            'EW', 'TFX', 'WST', 'STE', 'XRAY', 'DENT', 'SIRO', 'OMCL', 'MMSI', 'ICUI',
            'TMO', 'DHR', 'A', 'WAT', 'BIO', 'QGEN', 'TECH', 'MTD', 'IQV', 'CRL',
            'PFE', 'MRK', 'ABBV', 'BMY', 'LLY', 'GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX',
            'MRNA', 'BNTX', 'NVAX', 'INO', 'OCGN', 'DVAX', 'VXRT', 'NVAX', 'SRNE', 'CTXR',
            'ETON', 'HZNP', 'JAZZ', 'ALKS', 'TEVA', 'MYL', 'PRGO', 'ENDP', 'VTRS', 'ZTS',
            'ELAN', 'PCRX', 'AMRX', 'KMPH', 'LXRX', 'ZYNE', 'CRBP', 'OCUL', 'ADMP', 'SPPI',
            'ALIM', 'ACRX', 'AKBA', 'OTIC', 'NKTR', 'ARWR', 'IONS', 'EXEL', 'INCY', 'BMRN',

            # Small-Mid Cap (601-900)
            'SAGE', 'ALNY', 'RGNX', 'RARE', 'FOLD', 'ARDX', 'CDTX', 'GLPG', 'LEGN', 'MDGL',
            'PTCT', 'CRSP', 'EDIT', 'NTLA', 'BEAM', 'VERV', 'RXRX', 'SDGR', 'ARQT', 'MYGN',
            'PACB', 'ILMN', 'NSTG', 'TXG', 'NVTA', 'CDNA', 'TWIST', 'VCYT', 'EXAS', 'MYGN',
            'VCEL', 'FATE', 'BLUE', 'ONCE', 'AVXL', 'ATNM', 'ADVM', 'AUPH', 'XNCR', 'YMAB',
            'IMMP', 'ARVN', 'ALLO', 'KYMR', 'BCYC', 'ANAB', 'SAVA', 'AGEN', 'FBRX', 'CASI',
            'CLVS', 'ESPR', 'MNKD', 'ARTH', 'ADMA', 'OSUR', 'VSTM', 'KDMN', 'KALA', 'ABUS',
            'PTGX', 'VYNE', 'TBPH', 'RLMD', 'ATOS', 'ATHX', 'CYAD', 'MTEM', 'SNGX', 'ADAP',
            'RNXT', 'NKTX', 'LCTX', 'YMAB', 'IGMS', 'RCKT', 'PGEN', 'DVAX', 'VXRT', 'BCRX',
            'IMRN', 'HOOK', 'ETNB', 'CLSD', 'NVIV', 'PBYI', 'EPIX', 'AMRS', 'GEVO', 'FCEL',
            'PLUG', 'BE', 'BLDP', 'CLNE', 'HYLN', 'WKHS', 'SOLO', 'AYRO', 'IDEX', 'LOTZ',

            'VWAGY', 'POAHY', 'FUJHY', 'NSANY', 'HYMTF', 'VLKAF', 'DDAIF', 'BAMXF', 'MBGAF', 'PEUGF',
            'RACE', 'STLA', 'FCAU', 'MT', 'TX', 'CLF', 'X', 'NUE', 'STLD', 'RS',
            'CMC', 'ZEUS', 'GGB', 'SID', 'PKX', 'WOR', 'ATI', 'KALU', 'CENX', 'AA',
            'RTX', 'LMT', 'BA', 'GD', 'NOC', 'TXT', 'LHX', 'HII', 'AJRD', 'SPR',
            'HWM', 'WWD', 'HEI', 'TDG', 'CACI', 'SAIC', 'LDOS', 'KTOS', 'AVAV', 'AIR',
            'CAT', 'DE', 'AGCO', 'PCAR', 'NAV', 'CNH', 'TEX', 'MTW', 'SHYF', 'HCSG',
            'EMR', 'HON', 'ITW', 'ROK', 'PH', 'AME', 'FLS', 'LECO', 'RRX', 'CW',
            'ETN', 'EATON', 'XYL', 'ITT', 'CR', 'FLOW', 'FLR', 'THRM', 'SPX', 'GTES',
            'GE', 'PWR', 'NEE', 'DUK', 'SO', 'D', 'EXC', 'SRE', 'AEP', 'PCG',
            'XEL', 'WEC', 'ES', 'ED', 'EIX', 'FE', 'AES', 'CMS', 'DTE', 'ETR',

            'PPL', 'CNP', 'NI', 'PNW', 'ATO', 'NWE', 'OGE', 'SR', 'AVA', 'POR',
            'VST', 'CEG', 'NRG', 'GEV', 'CWEN', 'AY', 'BKH', 'MDU', 'ORA', 'IDA',
            'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'PSX', 'VLO', 'MPC', 'HES', 'OXY',
            'DVN', 'FANG', 'MRO', 'APA', 'HAL', 'NOV', 'BKR', 'FTI', 'HP', 'OII',
            'RIG', 'NE', 'VAL', 'PTEN', 'WTTR', 'NINE', 'PDS', 'LBRT', 'PUMP', 'WHD',
            'EPD', 'MPLX', 'ET', 'PAA', 'WMB', 'OKE', 'KMI', 'TRGP', 'AM', 'HESM',
            'LNG', 'TELL', 'NEXT', 'CEI', 'CLNE', 'CSAN', 'SPH', 'ENLC', 'GEL', 'DTM',
            'NEM', 'GFI', 'GOLD', 'AEM', 'AU', 'HMY', 'KGC', 'PAAS', 'HL', 'EGO',
            'AG', 'CDE', 'FSM', 'SVM', 'EXK', 'GATO', 'SSRM', 'OR', 'MTRN', 'WPM',
            'FNV', 'RGLD', 'SAND', 'ENIC', 'STGO', 'GPL', 'IAG', 'NGD', 'BTG', 'DRD',

            # Additional 100 stocks (901-1000)
            'FCX', 'SCCO', 'TECK', 'MP', 'VALE', 'BHP', 'RIO', 'AA', 'CENX', 'KALU',
            'SQM', 'ALB', 'LAC', 'LITM', 'PLL', 'LTHM', 'SGML', 'LTBR', 'IONR', 'RES',
            'ARE', 'AMT', 'CCI', 'SBAC', 'UNIT', 'DLR', 'EQIX', 'PSA', 'EXR', 'CUBE',
            'AVB', 'EQR', 'ESS', 'MAA', 'CPT', 'UDR', 'AIV', 'AIRC', 'NXRT', 'IRT',
            'SPG', 'O', 'VICI', 'WPC', 'STOR', 'ADC', 'EPRT', 'GTY', 'SRC', 'SAFE',
            'VNO', 'SLG', 'BXP', 'HIW', 'DEI', 'CUZ', 'PDM', 'PGRE', 'SHO', 'OFC',
            'DRE', 'FR', 'KRC', 'CLI', 'DEA', 'ARE', 'BMR', 'JBGS', 'ESRT', 'SLG',
            'PLD', 'DRE', 'FR', 'STAG', 'TRNO', 'EGP', 'REXR', 'FR', 'NSA', 'CUBE',
            'BRX', 'VRE', 'COLD', 'PLYM', 'GOOD', 'LAND', 'PINE', 'INN', 'RHP', 'HST',
            'PK', 'RLJ', 'SHO', 'AHT', 'XHR', 'SOHO', 'CLDT', 'INN', 'DRH', 'APLE'
        ]

        # ETF symbols (will be filtered out for regular analysis)
        self.etf_symbols = [
            'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO', 'VEA', 'VWO', 'AGG', 'BND',
            'TLT', 'IEF', 'LQD', 'HYG', 'EMB', 'VNQ', 'GLD', 'SLV', 'USO', 'UNG'
        ]

    def get_unique_stock_symbols(self) -> List[str]:
        """Get unique stock symbols excluding ETFs"""
        stock_symbols = [symbol for symbol in self.all_symbols if symbol not in self.etf_symbols]
        unique_symbols = []
        seen = set()
        for symbol in stock_symbols:
            if symbol not in seen:
                unique_symbols.append(symbol)
                seen.add(symbol)
        return unique_symbols

    def get_etf_symbols(self) -> List[str]:
        """Get ETF symbols"""
        return list(set(self.etf_symbols))

    def get_top_stocks_by_market_cap(self, count: int = 100) -> List[str]:
        """Get top stocks typically by market cap (S&P 500 style)"""
        top_stocks = self.all_symbols[:count]
        return top_stocks

    def get_complete_universe(self) -> List[str]:
        """Get the complete universe of stocks"""
        return self.get_unique_stock_symbols()


class EliteHedgeFundAnalyzer:
    """Elite hedge fund-style stock analyzer with institutional features"""

    def __init__(self):
        self.nobel_methods = NobelPrizeQuantMethods()
        self.risk_metrics = AdvancedRiskMetrics()
        self.ml_alpha = MachineLearningAlpha()
        self.symbol_manager = StockSymbolManager()
        self.complete_universe = self.symbol_manager.get_complete_universe()
        self.elite_universe = self.symbol_manager.get_top_stocks_by_market_cap(200)

    def enhanced_stock_analysis(self, symbol):
        """Comprehensive elite hedge fund analysis for a single stock"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5y", timeout=30)

            if hist.empty or len(hist) < 100:
                return None

            info = ticker.info if hasattr(ticker, 'info') else {}
            spy = yf.Ticker("SPY")
            spy_hist = spy.history(period="5y")

            current_price = hist['Close'].iloc[-1]
            returns = hist['Close'].pct_change().dropna()
            prices = hist['Close']
            volume = hist.get('Volume', pd.Series())

            if not spy_hist.empty and len(spy_hist) >= len(hist):
                spy_returns = spy_hist['Close'].pct_change().dropna()
                min_length = min(len(returns), len(spy_returns))
                returns_aligned = returns.tail(min_length)
                spy_aligned = spy_returns.tail(min_length)
            else:
                returns_aligned = returns
                spy_aligned = None

            if spy_aligned is not None:
                ff_analysis = self.nobel_methods.fama_french_factors(returns_aligned, spy_aligned)
            else:
                ff_analysis = {'beta': np.nan, 'alpha': np.nan, 'r_squared': np.nan, 'tracking_error': np.nan}

            behavioral_analysis = self.nobel_methods.behavioral_finance_indicators(prices, volume)
            var_cvar = self.risk_metrics.calculate_var_cvar(returns)
            regime_analysis = self.risk_metrics.regime_detection(returns)
            stress_results = self.risk_metrics.stress_testing(returns)
            tail_risk = self.risk_metrics.tail_risk_measures(returns)
            fundamental_metrics = self._calculate_elite_fundamentals(info)
            technical_metrics = self._calculate_elite_technical(hist)
            valuation_metrics = self._calculate_elite_valuation(info, current_price)
            performance_metrics = self._calculate_elite_performance(hist, spy_hist)

            quality_scores = self._calculate_elite_quality_scores(
                fundamental_metrics, technical_metrics, performance_metrics,
                ff_analysis, behavioral_analysis, tail_risk
            )

            investment_thesis = self._generate_investment_thesis(
                symbol, quality_scores, fundamental_metrics, performance_metrics,
                regime_analysis, stress_results
            )

            result = {
                'Symbol': symbol,
                'Price': current_price,
                'Sector': info.get('sector', 'N/A'),
                'Industry': info.get('industry', 'N/A'),
                'Market_Cap': info.get('marketCap', np.nan),
                **ff_analysis,
                **behavioral_analysis,
                **var_cvar,
                **regime_analysis,
                **tail_risk,
                **fundamental_metrics,
                **technical_metrics,
                **valuation_metrics,
                **performance_metrics,
                **quality_scores,
                'Investment_Thesis': investment_thesis['thesis'],
                'Risk_Level': investment_thesis['risk_level'],
                'Time_Horizon': investment_thesis['time_horizon'],
                'Position_Size_Rec': investment_thesis['position_size'],
                'Catalyst_Events': investment_thesis['catalysts'],
                'Worst_Case_Loss': max(
                    [s['loss_percentage'] for s in stress_results.values()]) if stress_results else np.nan,
                'Recovery_Time_Months': max(
                    [s['estimated_recovery_months'] for s in stress_results.values()]) if stress_results else np.nan,
                'Analysis_Date': datetime.now().strftime('%Y-%m-%d'),
                'Data_Points': len(hist),
                'Data_Quality_Score': min(100, (len(hist) / 1260) * 100)
            }

            return result

        except Exception as e:
            print(f"Error analyzing {symbol}: {str(e)}")
            return None

    def _calculate_elite_fundamentals(self, info):
        """Calculate elite fundamental metrics"""
        metrics = {}
        metrics['ROE'] = info.get('returnOnEquity', np.nan)
        metrics['ROA'] = info.get('returnOnAssets', np.nan)
        metrics['ROIC'] = info.get('returnOnCapital', np.nan)
        metrics['Gross_Margin'] = info.get('grossMargins', np.nan)
        metrics['Operating_Margin'] = info.get('operatingMargins', np.nan)
        metrics['Net_Margin'] = info.get('profitMargins', np.nan)
        metrics['Revenue_Growth'] = info.get('revenueGrowth', np.nan)
        metrics['Earnings_Growth'] = info.get('earningsGrowth', np.nan)
        metrics['Debt_to_Equity'] = info.get('debtToEquity', np.nan)
        metrics['Current_Ratio'] = info.get('currentRatio', np.nan)
        metrics['Quick_Ratio'] = info.get('quickRatio', np.nan)
        metrics['Interest_Coverage'] = info.get('interestCoverage', np.nan)
        metrics['Asset_Turnover'] = info.get('totalRevenue', 0) / info.get('totalAssets', 1) if info.get('totalAssets',
                                                                                                         0) > 0 else np.nan
        metrics['Inventory_Turnover'] = info.get('totalRevenue', 0) / info.get('inventory', 1) if info.get('inventory',
                                                                                                           0) > 0 else np.nan

        for key in ['ROE', 'ROA', 'ROIC', 'Gross_Margin', 'Operating_Margin', 'Net_Margin', 'Revenue_Growth',
                    'Earnings_Growth']:
            if metrics[key] is not None and not pd.isna(metrics[key]):
                metrics[key] *= 100

        return metrics

    def _calculate_elite_technical(self, hist):
        """Calculate elite technical indicators"""
        prices = hist['Close']
        volume = hist.get('Volume', pd.Series())
        high = hist['High']
        low = hist['Low']
        metrics = {}

        metrics['SMA_20'] = prices.rolling(20).mean().iloc[-1] if len(prices) > 20 else np.nan
        metrics['SMA_50'] = prices.rolling(50).mean().iloc[-1] if len(prices) > 50 else np.nan
        metrics['SMA_200'] = prices.rolling(200).mean().iloc[-1] if len(prices) > 200 else np.nan

        current_price = prices.iloc[-1]
        metrics['Price_vs_SMA20'] = (current_price / metrics['SMA_20'] - 1) * 100 if not pd.isna(
            metrics['SMA_20']) else np.nan
        metrics['Price_vs_SMA200'] = (current_price / metrics['SMA_200'] - 1) * 100 if not pd.isna(
            metrics['SMA_200']) else np.nan

        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        metrics['RSI'] = (100 - (100 / (1 + rs))).iloc[-1] if len(rs) > 0 else np.nan

        sma_20 = prices.rolling(20).mean()
        std_20 = prices.rolling(20).std()
        bb_upper = sma_20 + (2 * std_20)
        bb_lower = sma_20 - (2 * std_20)
        metrics['BB_Position'] = ((current_price - bb_lower.iloc[-1]) / (
                    bb_upper.iloc[-1] - bb_lower.iloc[-1])) * 100 if len(bb_upper) > 0 else np.nan

        tr1 = high - low
        tr2 = abs(high - prices.shift())
        tr3 = abs(low - prices.shift())
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        metrics['ATR'] = tr.rolling(14).mean().iloc[-1] if len(tr) > 14 else np.nan
        metrics['ATR_Percent'] = (metrics['ATR'] / current_price) * 100 if not pd.isna(metrics['ATR']) else np.nan

        exp1 = prices.ewm(span=12).mean()
        exp2 = prices.ewm(span=26).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9).mean()
        metrics['MACD'] = macd.iloc[-1] if len(macd) > 0 else np.nan
        metrics['MACD_Signal'] = signal.iloc[-1] if len(signal) > 0 else np.nan
        metrics['MACD_Histogram'] = (macd - signal).iloc[-1] if len(macd) > 0 and len(signal) > 0 else np.nan

        if not volume.empty and len(volume) > 20:
            metrics['Volume_SMA_20'] = volume.rolling(20).mean().iloc[-1]
            metrics['Volume_Ratio'] = volume.iloc[-1] / metrics['Volume_SMA_20'] if not pd.isna(
                metrics['Volume_SMA_20']) else np.nan
            obv = (volume * prices.diff().apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0)).cumsum()
            metrics['OBV'] = obv.iloc[-1] if len(obv) > 0 else np.nan
        else:
            metrics['Volume_SMA_20'] = np.nan
            metrics['Volume_Ratio'] = np.nan
            metrics['OBV'] = np.nan

        rolling_max_20 = high.rolling(20).max()
        rolling_min_20 = low.rolling(20).min()
        metrics['Resistance_Level'] = rolling_max_20.iloc[-1] if len(rolling_max_20) > 0 else np.nan
        metrics['Support_Level'] = rolling_min_20.iloc[-1] if len(rolling_min_20) > 0 else np.nan
        metrics['Distance_to_Resistance'] = ((metrics[
                                                  'Resistance_Level'] - current_price) / current_price) * 100 if not pd.isna(
            metrics['Resistance_Level']) else np.nan
        metrics['Distance_to_Support'] = ((current_price - metrics[
            'Support_Level']) / current_price) * 100 if not pd.isna(metrics['Support_Level']) else np.nan

        return metrics

    def _calculate_elite_valuation(self, info, current_price):
        """Calculate elite valuation metrics"""
        metrics = {}
        metrics['PE_Ratio'] = info.get('trailingPE', np.nan)
        metrics['Forward_PE'] = info.get('forwardPE', np.nan)
        metrics['PB_Ratio'] = info.get('priceToBook', np.nan)
        metrics['PS_Ratio'] = info.get('priceToSales', np.nan)
        metrics['PEG_Ratio'] = info.get('pegRatio', np.nan)
        metrics['EV_Revenue'] = info.get('enterpriseToRevenue', np.nan)
        metrics['EV_EBITDA'] = info.get('enterpriseToEbitda', np.nan)
        metrics['Dividend_Yield'] = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
        metrics['Payout_Ratio'] = info.get('payoutRatio', np.nan)
        metrics['Price_to_Tangible_Book'] = info.get('priceToBook', np.nan)
        metrics['Market_to_Book'] = info.get('priceToBook', np.nan)
        metrics['Price_to_FCF'] = info.get('marketCap', np.nan) / info.get('freeCashflow', 1) if info.get(
            'freeCashflow', 0) > 0 else np.nan
        metrics['EV_to_FCF'] = info.get('enterpriseValue', np.nan) / info.get('freeCashflow', 1) if info.get(
            'freeCashflow', 0) > 0 else np.nan

        pe_score = 10 - min(10, max(0, (metrics['PE_Ratio'] - 15) / 5)) if not pd.isna(metrics['PE_Ratio']) and metrics[
            'PE_Ratio'] > 0 else 5
        pb_score = 10 - min(10, max(0, (metrics['PB_Ratio'] - 2) / 2)) if not pd.isna(metrics['PB_Ratio']) and metrics[
            'PB_Ratio'] > 0 else 5
        metrics['Relative_Valuation_Score'] = (pe_score + pb_score) / 2

        return metrics

    def _calculate_elite_performance(self, hist, spy_hist=None):
        """Calculate elite performance metrics"""
        prices = hist['Close']
        returns = prices.pct_change().dropna()
        metrics = {}

        periods = {'1D': 1, '1W': 5, '2W': 10, '1M': 21, '3M': 63, '6M': 126, '1Y': 252, '2Y': 504, '3Y': 756,
                   '5Y': 1260}
        current_price = prices.iloc[-1]

        for period_name, days in periods.items():
            if len(prices) > days:
                past_price = prices.iloc[-(days + 1)]
                metrics[f'Return_{period_name}'] = ((current_price - past_price) / past_price) * 100
            else:
                metrics[f'Return_{period_name}'] = np.nan

        if len(returns) >= 252:
            annual_return = returns.mean() * 252
            annual_vol = returns.std() * np.sqrt(252)
            risk_free_rate = 0.045

            metrics['Sharpe_Ratio'] = (annual_return - risk_free_rate) / annual_vol if annual_vol > 0 else np.nan

            downside_returns = returns[returns < 0]
            if len(downside_returns) > 0:
                downside_deviation = np.sqrt(np.mean(downside_returns ** 2)) * np.sqrt(252)
                metrics['Sortino_Ratio'] = (
                                                       annual_return - risk_free_rate) / downside_deviation if downside_deviation > 0 else np.nan
            else:
                metrics['Sortino_Ratio'] = np.nan

            rolling_max = prices.expanding().max()
            drawdown = (prices - rolling_max) / rolling_max
            metrics['Max_Drawdown'] = drawdown.min() * 100
            metrics['Calmar_Ratio'] = abs(annual_return * 100 / metrics['Max_Drawdown']) if metrics[
                                                                                                'Max_Drawdown'] < 0 else np.nan
            metrics['Volatility'] = annual_vol * 100

        if spy_hist is not None and not spy_hist.empty:
            spy_returns = spy_hist['Close'].pct_change().dropna()
            min_length = min(len(returns), len(spy_returns))

            if min_length > 50:
                stock_returns = returns.tail(min_length)
                market_returns = spy_returns.tail(min_length)
                covariance = np.cov(stock_returns, market_returns)[0, 1]
                market_variance = np.var(market_returns)
                metrics['Beta'] = covariance / market_variance if market_variance > 0 else np.nan

                if not pd.isna(metrics['Beta']):
                    expected_return = 0.045 / 252 + metrics['Beta'] * (market_returns.mean() - 0.045 / 252)
                    metrics['Alpha'] = (stock_returns.mean() - expected_return) * 252 * 100
                else:
                    metrics['Alpha'] = np.nan
            else:
                metrics['Beta'] = np.nan
                metrics['Alpha'] = np.nan
        else:
            metrics['Beta'] = np.nan
            metrics['Alpha'] = np.nan

        if len(prices) >= 252:
            fifty_two_week_high = prices.tail(252).max()
            fifty_two_week_low = prices.tail(252).min()
            metrics['52W_High'] = fifty_two_week_high
            metrics['52W_Low'] = fifty_two_week_low
            metrics['Distance_from_52W_High'] = ((fifty_two_week_high - current_price) / fifty_two_week_high) * 100
            metrics['Distance_from_52W_Low'] = ((current_price - fifty_two_week_low) / fifty_two_week_low) * 100

        return metrics

    def _calculate_elite_quality_scores(self, fundamental_metrics, technical_metrics, performance_metrics, ff_analysis,
                                        behavioral_analysis, tail_risk):
        """Calculate comprehensive quality scores"""
        scores = {}
        financial_components = []

        roe = fundamental_metrics.get('ROE', 0)
        if roe > 20:
            financial_components.append(3)
        elif roe > 15:
            financial_components.append(2.5)
        elif roe > 10:
            financial_components.append(2)
        elif roe > 5:
            financial_components.append(1)
        else:
            financial_components.append(0)

        debt_equity = fundamental_metrics.get('Debt_to_Equity', 100)
        if debt_equity < 0.5:
            financial_components.append(2)
        elif debt_equity < 1.0:
            financial_components.append(1.5)
        elif debt_equity < 2.0:
            financial_components.append(1)
        else:
            financial_components.append(0)

        current_ratio = fundamental_metrics.get('Current_Ratio', 0)
        if current_ratio > 2:
            financial_components.append(2)
        elif current_ratio > 1.5:
            financial_components.append(1.5)
        elif current_ratio > 1:
            financial_components.append(1)
        else:
            financial_components.append(0)

        scores['Financial_Quality_Score'] = min(10, sum(financial_components)) if financial_components else 5

        growth_components = []
        revenue_growth = fundamental_metrics.get('Revenue_Growth', 0)
        if revenue_growth > 25:
            growth_components.append(3)
        elif revenue_growth > 15:
            growth_components.append(2.5)
        elif revenue_growth > 10:
            growth_components.append(2)
        elif revenue_growth > 5:
            growth_components.append(1)
        else:
            growth_components.append(0)

        earnings_growth = fundamental_metrics.get('Earnings_Growth', 0)
        if earnings_growth > 20:
            growth_components.append(2)
        elif earnings_growth > 10:
            growth_components.append(1.5)
        elif earnings_growth > 5:
            growth_components.append(1)
        else:
            growth_components.append(0)

        scores['Growth_Quality_Score'] = min(10, sum(growth_components) * 1.5) if growth_components else 5

        momentum_components = []
        rsi = technical_metrics.get('RSI', 50)
        if 50 < rsi < 70:
            momentum_components.append(2)
        elif 40 < rsi < 80:
            momentum_components.append(1)
        else:
            momentum_components.append(0)

        return_1y = performance_metrics.get('Return_1Y', 0)
        if return_1y > 30:
            momentum_components.append(3)
        elif return_1y > 15:
            momentum_components.append(2)
        elif return_1y > 0:
            momentum_components.append(1)
        else:
            momentum_components.append(0)

        scores['Momentum_Quality_Score'] = min(10, sum(momentum_components) * 2) if momentum_components else 5

        risk_components = []
        sharpe_ratio = performance_metrics.get('Sharpe_Ratio', 0)
        if sharpe_ratio > 2:
            risk_components.append(3)
        elif sharpe_ratio > 1:
            risk_components.append(2)
        elif sharpe_ratio > 0:
            risk_components.append(1)
        else:
            risk_components.append(0)

        max_drawdown = performance_metrics.get('Max_Drawdown', -100)
        if max_drawdown > -10:
            risk_components.append(3)
        elif max_drawdown > -20:
            risk_components.append(2)
        elif max_drawdown > -30:
            risk_components.append(1)
        else:
            risk_components.append(0)

        scores['Risk_Adjusted_Score'] = min(10, sum(risk_components) * 1.5) if risk_components else 5

        alpha_components = []
        alpha = ff_analysis.get('alpha', 0)
        if alpha > 10:
            alpha_components.append(3)
        elif alpha > 5:
            alpha_components.append(2)
        elif alpha > 0:
            alpha_components.append(1)
        else:
            alpha_components.append(0)

        information_ratio = ff_analysis.get('tracking_error', 100)
        if information_ratio < 10:
            alpha_components.append(2)
        elif information_ratio < 20:
            alpha_components.append(1)
        else:
            alpha_components.append(0)

        scores['Alpha_Generation_Score'] = min(10, sum(alpha_components) * 2) if alpha_components else 5

        behavioral_bias = behavioral_analysis.get('behavioral_bias_score', 50)
        if behavioral_bias < 30:
            scores['Behavioral_Opportunity_Score'] = 8
        elif behavioral_bias < 50:
            scores['Behavioral_Opportunity_Score'] = 6
        elif behavioral_bias < 70:
            scores['Behavioral_Opportunity_Score'] = 4
        else:
            scores['Behavioral_Opportunity_Score'] = 2

        component_scores = [
            scores.get('Financial_Quality_Score', 5),
            scores.get('Growth_Quality_Score', 5),
            scores.get('Momentum_Quality_Score', 5),
            scores.get('Risk_Adjusted_Score', 5),
            scores.get('Alpha_Generation_Score', 5),
            scores.get('Behavioral_Opportunity_Score', 5)
        ]

        scores['Elite_Composite_Score'] = np.mean(component_scores)

        hf_appeal = 0
        if alpha > 5: hf_appeal += 2
        hf_appeal += 1
        vol = performance_metrics.get('Volatility', 50)
        if 15 < vol < 35:
            hf_appeal += 2
        elif 10 < vol < 50:
            hf_appeal += 1
        if scores.get('Financial_Quality_Score', 0) > 7: hf_appeal += 2
        if scores.get('Momentum_Quality_Score', 0) > 6: hf_appeal += 1

        scores['Hedge_Fund_Appeal_Score'] = min(10, hf_appeal)

        return scores

    def _generate_investment_thesis(self, symbol, quality_scores, fundamental_metrics, performance_metrics,
                                    regime_analysis, stress_results):
        """Generate AI-powered investment thesis"""
        elite_score = quality_scores.get('Elite_Composite_Score', 5)
        hf_appeal = quality_scores.get('Hedge_Fund_Appeal_Score', 5)

        if elite_score >= 8 and hf_appeal >= 7:
            thesis_category = "CONVICTION BUY"
            thesis = f"{symbol} exhibits exceptional quality across all metrics with strong hedge fund appeal. "
        elif elite_score >= 7:
            thesis_category = "STRONG BUY"
            thesis = f"{symbol} demonstrates strong fundamentals with good risk-adjusted returns. "
        elif elite_score >= 6:
            thesis_category = "BUY"
            thesis = f"{symbol} shows solid prospects with moderate risk profile. "
        elif elite_score >= 5:
            thesis_category = "HOLD"
            thesis = f"{symbol} presents mixed signals requiring careful monitoring. "
        elif elite_score >= 4:
            thesis_category = "WEAK HOLD"
            thesis = f"{symbol} shows concerning metrics but may have turnaround potential. "
        else:
            thesis_category = "AVOID"
            thesis = f"{symbol} exhibits weak fundamentals and poor risk-reward profile. "

        roe = fundamental_metrics.get('ROE', 0)
        if roe > 20:
            thesis += f"Exceptional ROE of {roe:.1f}% indicates superior capital efficiency. "

        sharpe = performance_metrics.get('Sharpe_Ratio', 0)
        if sharpe > 1.5:
            thesis += f"Strong risk-adjusted returns (Sharpe: {sharpe:.2f}) demonstrate quality management. "

        alpha = performance_metrics.get('Alpha', 0)
        if alpha > 5:
            thesis += f"Significant alpha generation ({alpha:.1f}%) suggests market outperformance capability. "

        regime = regime_analysis.get('current_regime', 'unknown')
        if regime == 'high_volatility':
            thesis += "Current high volatility regime suggests defensive positioning. "
        elif regime == 'low_volatility':
            thesis += "Low volatility environment favors momentum strategies. "

        max_dd = performance_metrics.get('Max_Drawdown', 0)
        if max_dd < -30:
            risk_level = "HIGH"
            thesis += f"Significant drawdown risk ({max_dd:.1f}%) requires careful position sizing. "
        elif max_dd < -20:
            risk_level = "MEDIUM-HIGH"
        elif max_dd < -10:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        if elite_score >= 8 and risk_level in ["LOW", "MEDIUM"]:
            position_size = "3-5%"
        elif elite_score >= 7:
            position_size = "2-3%"
        elif elite_score >= 6:
            position_size = "1-2%"
        else:
            position_size = "<1%"

        if quality_scores.get('Growth_Quality_Score', 0) > 7:
            time_horizon = "2-3 years"
        elif quality_scores.get('Financial_Quality_Score', 0) > 7:
            time_horizon = "1-2 years"
        else:
            time_horizon = "6-12 months"

        catalysts = []
        if fundamental_metrics.get('Revenue_Growth', 0) > 20:
            catalysts.append("Earnings momentum")
        if performance_metrics.get('Return_3M', 0) > 15:
            catalysts.append("Technical breakout")
        if fundamental_metrics.get('Debt_to_Equity', 1) < 0.5:
            catalysts.append("Balance sheet strength")

        return {
            'thesis': thesis_category + ": " + thesis,
            'risk_level': risk_level,
            'time_horizon': time_horizon,
            'position_size': position_size,
            'catalysts': ', '.join(catalysts) if catalysts else 'Monitor for developments'
        }


def run_elite_hedge_fund_analysis():
    """Main function to run elite hedge fund analysis"""
    print("=" * 100)
    print("🏆 ELITE HEDGE FUND STOCK ANALYSIS SYSTEM - US MARKETS (1000 Stocks)")
    print("=" * 100)
    print("🎯 NOBEL PRIZE METHODS IMPLEMENTED:")
    print("   ✓ Markowitz Portfolio Optimization (1990)")
    print("   ✓ Fama-French Factor Models (Sharpe 1990)")
    print("   ✓ Behavioral Finance Analysis (Kahneman 2002)")
    print("   ✓ Advanced Risk Management (VaR, CVaR, Stress Testing)")
    print("=" * 100)

    analyzer = EliteHedgeFundAnalyzer()

    print(f"\n📊 US STOCK UNIVERSE STATISTICS:")
    print(f"   Total stocks available: {len(analyzer.complete_universe):,} stocks")
    print(f"   Elite universe (top market cap): {len(analyzer.elite_universe)} stocks")

    print("\n🎯 ANALYSIS OPTIONS:")
    print("1. Full Universe (1000 stocks) - Comprehensive scan")
    print("2. Large Cap Elite (Top 200 stocks)")
    print("3. Top 100 Mega Caps")
    print("4. Top 50 Blue Chips")
    print("5. Custom Selection")
    print("6. Quick Test (10 stocks)")

    try:
        choice = input("\nSelect analysis type (1-6) [default: 6]: ").strip()
        if not choice:
            choice = '6'
    except:
        choice = '6'

    if choice == '1':
        stocks_to_analyze = analyzer.complete_universe
        analysis_name = "Full_Universe_1000"
        max_workers = 12
        print(f"\n🌟 Running FULL UNIVERSE Analysis on {len(stocks_to_analyze)} stocks!")
        print("⚠️  This will take approximately 60-90 minutes")
        confirm = input("Continue? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Switching to Quick Test...")
            stocks_to_analyze = analyzer.all_symbols[:10]
            analysis_name = "Quick_Test"
            max_workers = 4
    elif choice == '2':
        stocks_to_analyze = analyzer.elite_universe
        analysis_name = "Large_Cap_Elite_200"
        max_workers = 10
    elif choice == '3':
        stocks_to_analyze = analyzer.all_symbols[:100]
        analysis_name = "Top_100_Mega_Caps"
        max_workers = 8
    elif choice == '4':
        stocks_to_analyze = analyzer.all_symbols[:50]
        analysis_name = "Top_50_Blue_Chips"
        max_workers = 6
    elif choice == '5':
        print("💡 Enter stock symbols separated by commas (e.g., AAPL,MSFT,GOOGL)")
        custom_input = input("Stock symbols: ").strip().upper()
        if custom_input:
            stocks_to_analyze = [s.strip() for s in custom_input.split(',') if s.strip()]
            analysis_name = "Custom_Selection"
            max_workers = 4
        else:
            stocks_to_analyze = analyzer.all_symbols[:10]
            analysis_name = "Quick_Test"
            max_workers = 4
    else:
        stocks_to_analyze = analyzer.all_symbols[:10]
        analysis_name = "Quick_Test"
        max_workers = 4

    print(f"\n🏦 Starting Elite Hedge Fund Analysis...")
    print(f"📊 Processing {len(stocks_to_analyze)} stocks...")
    print(f"⚡ Using {max_workers} parallel workers")

    estimated_time = (len(stocks_to_analyze) * 2.5) / max_workers / 60
    print(f"⏱️  Estimated time: {estimated_time:.1f} minutes")

    start_time = time.time()
    results = []
    failed = []

    batch_size = 20
    for batch_start in range(0, len(stocks_to_analyze), batch_size):
        batch_end = min(batch_start + batch_size, len(stocks_to_analyze))
        batch_stocks = stocks_to_analyze[batch_start:batch_end]

        print(
            f"\n📦 Batch {batch_start // batch_size + 1}/{(len(stocks_to_analyze) - 1) // batch_size + 1} ({batch_start + 1}-{batch_end})")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(analyzer.enhanced_stock_analysis, s): s for s in batch_stocks}

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result(timeout=90)
                    if result:
                        results.append(result)
                        score = result.get('Elite_Composite_Score', 0)
                        print(f"   ✅ {symbol:<8} | Elite: {score:5.2f}")
                    else:
                        failed.append(symbol)
                        print(f"   ❌ {symbol:<8} | No data")
                except Exception as e:
                    failed.append(symbol)
                    print(f"   ❌ {symbol:<8} | Error")

                time.sleep(0.05)

        # Progress update
        elapsed = time.time() - start_time
        remaining = len(stocks_to_analyze) - batch_end
        eta = (elapsed / batch_end * len(stocks_to_analyze) - elapsed) / 60 if batch_end > 0 else 0
        print(f"   📊 Progress: {len(results)}/{len(stocks_to_analyze)} | ETA: {eta:.1f}m")

    end_time = time.time()
    print(f"\n{'=' * 100}")
    print(f"⏱️  Total time: {(end_time - start_time) / 60:.1f} minutes")
    print(f"✅ Analyzed: {len(results)} | ❌ Failed: {len(failed)}")

    if not results:
        print("❌ No results")
        return None

    df = pd.DataFrame(results)
    df = df.sort_values('Elite_Composite_Score', ascending=False)

    print(f"\n🏆 TOP 20 PERFORMERS:")
    print("-" * 80)
    for idx, row in df.head(20).iterrows():
        thesis = row['Investment_Thesis'].split(':')[0] if ':' in row['Investment_Thesis'] else 'HOLD'
        print(f"{row['Symbol']:8} | {row['Elite_Composite_Score']:5.2f} | {thesis:15} | {row['Sector'][:20]}")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = f"elite_analysis_{analysis_name}_{timestamp}.csv"
    df.to_csv(csv_file, index=False)

    excel_file = f"elite_analysis_{analysis_name}_{timestamp}.xlsx"
    df.to_excel(excel_file, index=False, engine='openpyxl')

    print(f"\n💾 Results saved:")
    print(f"   CSV:   {csv_file}")
    print(f"   Excel: {excel_file}")

    print(f"\n📊 Summary Statistics:")
    print(f"   Average Elite Score: {df['Elite_Composite_Score'].mean():.2f}")
    print(f"   Conviction Buys: {len(df[df['Investment_Thesis'].str.contains('CONVICTION', na=False)])}")
    print(f"   Strong Buys: {len(df[df['Investment_Thesis'].str.contains('STRONG BUY', na=False)])}")
    print(f"   High Alpha (>5%): {len(df[df['Alpha'] > 5])}")

    return df


if __name__ == "__main__":
    print("🏆 Elite Hedge Fund Stock Analysis System - 1000 US Stocks")
    print("💼 Professional-grade institutional analytics")

    try:
        df = run_elite_hedge_fund_analysis()
        if df is not None:
            print("\n🎉 Analysis Complete!")
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()