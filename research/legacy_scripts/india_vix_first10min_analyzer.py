"""
INDIA VIX FIRST 10 MINUTES VOLATILITY ANALYZER
=============================================

Analyzes India VIX volatility patterns in the first 10 minutes of trading
over the last 200 days to validate market open volatility strategies.

Features:
- Fetches 1-minute India VIX data for first 10 minutes (9:15-9:25 AM)
- Analyzes volatility patterns and statistics
- Calculates surge ratios and movement patterns
- Exports to Excel with Windows-friendly encoding
- Provides actionable insights for ATM±2 option strategies
"""

import asyncio
import aiohttp
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import json
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('india_vix_analysis.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class IndiaVIXAnalyzer:
    """Analyze India VIX first 10 minutes volatility patterns"""

    def __init__(self):
        print("INDIA VIX FIRST 10 MINUTES VOLATILITY ANALYZER")
        print("=" * 60)

        # Configuration
        self.api_key: Optional[str] = None
        self.access_token: Optional[str] = None
        self.credentials_file = "kite_token.txt"
        self.base_url = "https://api.kite.trade"

        # India VIX details
        self.vix_token = "264969"  # India VIX instrument token
        self.vix_symbol = "INDIA VIX"

        # Session management
        self.session: Optional[aiohttp.ClientSession] = None

        # Analysis parameters
        self.analysis_days = 200  # Last 200 trading days
        self.first_10_minutes = [
            "09:15", "09:16", "09:17", "09:18", "09:19",
            "09:20", "09:21", "09:22", "09:23", "09:24", "09:25"
        ]

        # Results storage
        self.vix_data = []

    async def load_credentials(self) -> bool:
        """Load Kite API credentials"""
        try:
            if not os.path.exists(self.credentials_file):
                logger.error(f"{self.credentials_file} not found!")
                print(f"ERROR: Please create {self.credentials_file} with:")
                print("API_KEY=your_api_key")
                print("ACCESS_TOKEN=your_access_token")
                return False

            with open(self.credentials_file, 'r') as f:
                lines = f.readlines()

            credentials = {}
            for line in lines:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    credentials[key] = value

            self.api_key = credentials.get('API_KEY')
            self.access_token = credentials.get('ACCESS_TOKEN')

            if not self.api_key or not self.access_token:
                logger.error("Missing API_KEY or ACCESS_TOKEN")
                return False

            logger.info("Credentials loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            return False

    async def get_session(self):
        """Get or create aiohttp session"""
        if not self.session or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=3,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=300
            )

            timeout = aiohttp.ClientTimeout(total=30)

            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'Authorization': f'token {self.api_key}:{self.access_token}',
                    'X-Kite-Version': '3'
                }
            )
        return self.session

    def get_last_trading_days(self, days: int) -> List[str]:
        """Get last N trading days excluding current day"""
        trading_days = []
        current_date = datetime.now() - timedelta(days=1)  # Start from yesterday

        while len(trading_days) < days:
            # Skip weekends (Saturday=5, Sunday=6)
            if current_date.weekday() < 5:
                trading_days.append(current_date.strftime('%Y-%m-%d'))
            current_date -= timedelta(days=1)

        trading_days.reverse()  # Oldest to newest
        logger.info(f"Analyzing {days} trading days: {trading_days[0]} to {trading_days[-1]}")
        return trading_days

    async def fetch_vix_minute_data(self, date: str) -> Optional[Dict]:
        """Fetch 1-minute India VIX data for a specific date"""
        try:
            await asyncio.sleep(0.35)  # Rate limiting - 3 req/sec

            # Create date range for the trading day (9:15 AM to 3:30 PM)
            from_time = f"{date} 09:15:00"
            to_time = f"{date} 15:30:00"

            session = await self.get_session()
            url = f"{self.base_url}/instruments/historical/{self.vix_token}/minute"
            params = {'from': from_time, 'to': to_time}

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'success':
                        candles = data.get('data', {}).get('candles', [])

                        # Extract first 10 minutes data
                        first_10_min_data = []

                        for candle in candles:
                            timestamp_str = candle[0]
                            open_val = candle[1]
                            high_val = candle[2]
                            low_val = candle[3]
                            close_val = candle[4]

                            # Parse timestamp
                            dt = datetime.fromisoformat(timestamp_str.replace('+0530', ''))
                            time_str = dt.strftime("%H:%M")

                            # Only collect first 10 minutes
                            if time_str in self.first_10_minutes:
                                first_10_min_data.append({
                                    'date': date,
                                    'time': time_str,
                                    'timestamp': dt,
                                    'open': open_val,
                                    'high': high_val,
                                    'low': low_val,
                                    'close': close_val
                                })

                        return {
                            'date': date,
                            'first_10_min': first_10_min_data,
                            'total_candles': len(candles)
                        }

                elif response.status == 429:  # Rate limit
                    logger.warning(f"Rate limited for {date}, waiting...")
                    await asyncio.sleep(2)
                    return await self.fetch_vix_minute_data(date)  # Retry
                else:
                    logger.warning(f"HTTP {response.status} for India VIX on {date}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching India VIX data for {date}: {e}")
            return None

    async def analyze_all_trading_days(self):
        """Fetch and analyze India VIX data for all trading days"""
        logger.info(f"Starting analysis of India VIX for last {self.analysis_days} trading days...")

        trading_days = self.get_last_trading_days(self.analysis_days)
        total_days = len(trading_days)
        completed_days = 0

        print(f"\nFetching India VIX data for {total_days} trading days...")
        print("This may take 5-10 minutes due to API rate limits...")

        start_time = time.time()

        for date in trading_days:
            try:
                day_data = await self.fetch_vix_minute_data(date)

                if day_data and day_data['first_10_min']:
                    # Add daily analysis
                    daily_analysis = self.analyze_daily_first_10_minutes(day_data)
                    day_data['analysis'] = daily_analysis
                    self.vix_data.append(day_data)

                completed_days += 1

                # Progress update
                if completed_days % 10 == 0 or completed_days == total_days:
                    progress = (completed_days / total_days) * 100
                    elapsed = time.time() - start_time
                    print(f"Progress: {completed_days}/{total_days} ({progress:.1f}%) - "
                          f"Elapsed: {elapsed:.1f}s - Latest: {date}")

            except Exception as e:
                logger.error(f"Error processing {date}: {e}")

        end_time = time.time()
        successful_days = len(self.vix_data)

        logger.info(f"Data collection completed in {end_time - start_time:.1f}s")
        logger.info(f"Success rate: {successful_days}/{total_days} days")

        return successful_days > 0

    def analyze_daily_first_10_minutes(self, day_data: Dict) -> Dict:
        """Analyze first 10 minutes VIX movement for a single day"""
        try:
            first_10_min = day_data['first_10_min']

            if not first_10_min:
                return {}

            # Get opening and 10-minute values
            opening_vix = first_10_min[0]['open']  # 9:15 open
            ten_min_vix = first_10_min[-1]['close']  # 9:25 close

            # Calculate min/max in first 10 minutes
            high_values = [candle['high'] for candle in first_10_min]
            low_values = [candle['low'] for candle in first_10_min]

            max_vix = max(high_values)
            min_vix = min(low_values)

            # Calculate movements
            absolute_change = ten_min_vix - opening_vix
            percent_change = (absolute_change / opening_vix) * 100 if opening_vix > 0 else 0

            # Calculate range
            total_range = max_vix - min_vix
            range_percent = (total_range / opening_vix) * 100 if opening_vix > 0 else 0

            # Determine volatility classification
            if abs(percent_change) >= 5:
                volatility_class = "EXTREME"
            elif abs(percent_change) >= 3:
                volatility_class = "HIGH"
            elif abs(percent_change) >= 1.5:
                volatility_class = "MODERATE"
            elif abs(percent_change) >= 0.5:
                volatility_class = "LOW"
            else:
                volatility_class = "MINIMAL"

            # Direction
            direction = "UP" if absolute_change > 0 else "DOWN" if absolute_change < 0 else "FLAT"

            return {
                'opening_vix': round(opening_vix, 2),
                'ten_min_vix': round(ten_min_vix, 2),
                'max_vix': round(max_vix, 2),
                'min_vix': round(min_vix, 2),
                'absolute_change': round(absolute_change, 2),
                'percent_change': round(percent_change, 2),
                'total_range': round(total_range, 2),
                'range_percent': round(range_percent, 2),
                'volatility_class': volatility_class,
                'direction': direction,
                'trading_minutes': len(first_10_min)
            }

        except Exception as e:
            logger.error(f"Error in daily analysis: {e}")
            return {}

    def create_comprehensive_analysis(self) -> pd.DataFrame:
        """Create comprehensive DataFrame with all analysis"""
        logger.info("Creating comprehensive analysis DataFrame...")

        analysis_data = []

        for day_data in self.vix_data:
            date = day_data['date']
            analysis = day_data.get('analysis', {})
            first_10_min = day_data.get('first_10_min', [])

            if analysis:
                row = {
                    'Date': date,
                    'Day_of_Week': datetime.strptime(date, '%Y-%m-%d').strftime('%A'),
                    'Opening_VIX': analysis.get('opening_vix', 0),
                    'Ten_Min_VIX': analysis.get('ten_min_vix', 0),
                    'Max_VIX': analysis.get('max_vix', 0),
                    'Min_VIX': analysis.get('min_vix', 0),
                    'Absolute_Change': analysis.get('absolute_change', 0),
                    'Percent_Change': analysis.get('percent_change', 0),
                    'Total_Range': analysis.get('total_range', 0),
                    'Range_Percent': analysis.get('range_percent', 0),
                    'Volatility_Class': analysis.get('volatility_class', 'UNKNOWN'),
                    'Direction': analysis.get('direction', 'UNKNOWN'),
                    'Trading_Minutes': analysis.get('trading_minutes', 0)
                }

                # Add minute-by-minute data
                for i, minute_data in enumerate(first_10_min):
                    time_key = minute_data['time'].replace(':', '_')
                    row[f'VIX_{time_key}'] = round(minute_data['close'], 2)

                analysis_data.append(row)

        df = pd.DataFrame(analysis_data)

        # Sort by date (newest first)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date', ascending=False)
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')  # Convert back to string

        logger.info(f"Created analysis DataFrame with {len(df)} days")
        return df

    def calculate_summary_statistics(self, df: pd.DataFrame) -> Dict:
        """Calculate comprehensive summary statistics"""
        if df.empty:
            return {}

        stats = {
            'total_days': len(df),
            'avg_opening_vix': df['Opening_VIX'].mean(),
            'avg_percent_change': df['Percent_Change'].mean(),
            'avg_range_percent': df['Range_Percent'].mean(),

            # Volatility class distribution
            'extreme_days': len(df[df['Volatility_Class'] == 'EXTREME']),
            'high_vol_days': len(df[df['Volatility_Class'] == 'HIGH']),
            'moderate_vol_days': len(df[df['Volatility_Class'] == 'MODERATE']),
            'low_vol_days': len(df[df['Volatility_Class'] == 'LOW']),
            'minimal_vol_days': len(df[df['Volatility_Class'] == 'MINIMAL']),

            # Direction distribution
            'up_days': len(df[df['Direction'] == 'UP']),
            'down_days': len(df[df['Direction'] == 'DOWN']),
            'flat_days': len(df[df['Direction'] == 'FLAT']),

            # Percentiles
            'percent_change_95th': df['Percent_Change'].quantile(0.95),
            'percent_change_90th': df['Percent_Change'].quantile(0.90),
            'percent_change_75th': df['Percent_Change'].quantile(0.75),
            'percent_change_50th': df['Percent_Change'].quantile(0.50),
            'percent_change_25th': df['Percent_Change'].quantile(0.25),
            'percent_change_10th': df['Percent_Change'].quantile(0.10),
            'percent_change_5th': df['Percent_Change'].quantile(0.05),

            # Range statistics
            'max_range_percent': df['Range_Percent'].max(),
            'avg_range_percent_extreme': df[df['Volatility_Class'] == 'EXTREME']['Range_Percent'].mean() if len(
                df[df['Volatility_Class'] == 'EXTREME']) > 0 else 0,

            # Day of week analysis
            'best_day': df.groupby('Day_of_Week')['Range_Percent'].mean().idxmax() if not df.empty else 'N/A',
            'worst_day': df.groupby('Day_of_Week')['Range_Percent'].mean().idxmin() if not df.empty else 'N/A'
        }

        # Calculate probabilities for strategy validation
        high_vol_days = len(df[df['Range_Percent'] >= 3.0])  # Days with >=3% range
        stats['high_volatility_probability'] = (high_vol_days / len(df)) * 100 if len(df) > 0 else 0

        extreme_move_days = len(df[abs(df['Percent_Change']) >= 2.0])  # Days with >=2% move
        stats['extreme_move_probability'] = (extreme_move_days / len(df)) * 100 if len(df) > 0 else 0

        return stats

    def save_to_excel(self, df: pd.DataFrame, stats: Dict) -> str:
        """Save analysis to Excel with Windows-friendly encoding"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # Use ASCII-safe filename
            filename = f"India_VIX_First_10Min_Analysis_{timestamp}.xlsx"

            logger.info(f"Creating Excel file: {filename}")

            with pd.ExcelWriter(filename, engine='openpyxl') as writer:

                # Sheet 1: Daily Analysis
                df.to_excel(writer, sheet_name='Daily_Analysis', index=False)
                logger.info("Created sheet: Daily_Analysis")

                # Sheet 2: Summary Statistics
                stats_df = pd.DataFrame([
                    ['Total Trading Days', stats.get('total_days', 0)],
                    ['Average Opening VIX', round(stats.get('avg_opening_vix', 0), 2)],
                    ['Average % Change (10min)', round(stats.get('avg_percent_change', 0), 2)],
                    ['Average Range %', round(stats.get('avg_range_percent', 0), 2)],
                    ['', ''],
                    ['VOLATILITY DISTRIBUTION', ''],
                    ['Extreme Days (>=5%)', stats.get('extreme_days', 0)],
                    ['High Vol Days (>=3%)', stats.get('high_vol_days', 0)],
                    ['Moderate Vol Days (>=1.5%)', stats.get('moderate_vol_days', 0)],
                    ['Low Vol Days (>=0.5%)', stats.get('low_vol_days', 0)],
                    ['Minimal Vol Days (<0.5%)', stats.get('minimal_vol_days', 0)],
                    ['', ''],
                    ['DIRECTION DISTRIBUTION', ''],
                    ['Up Days', stats.get('up_days', 0)],
                    ['Down Days', stats.get('down_days', 0)],
                    ['Flat Days', stats.get('flat_days', 0)],
                    ['', ''],
                    ['STRATEGY INSIGHTS', ''],
                    ['High Volatility Days (>=3% range)', f"{stats.get('high_volatility_probability', 0):.1f}%"],
                    ['Extreme Move Days (>=2% change)', f"{stats.get('extreme_move_probability', 0):.1f}%"],
                    ['Best Day of Week', stats.get('best_day', 'N/A')],
                    ['Worst Day of Week', stats.get('worst_day', 'N/A')],
                    ['', ''],
                    ['PERCENTILES (% Change)', ''],
                    ['95th Percentile', round(stats.get('percent_change_95th', 0), 2)],
                    ['90th Percentile', round(stats.get('percent_change_90th', 0), 2)],
                    ['75th Percentile', round(stats.get('percent_change_75th', 0), 2)],
                    ['50th Percentile (Median)', round(stats.get('percent_change_50th', 0), 2)],
                    ['25th Percentile', round(stats.get('percent_change_25th', 0), 2)],
                    ['10th Percentile', round(stats.get('percent_change_10th', 0), 2)],
                    ['5th Percentile', round(stats.get('percent_change_5th', 0), 2)]
                ], columns=['Metric', 'Value'])

                stats_df.to_excel(writer, sheet_name='Summary_Statistics', index=False)
                logger.info("Created sheet: Summary_Statistics")

                # Sheet 3: Volatility Class Analysis
                if not df.empty:
                    vol_class_analysis = df.groupby('Volatility_Class').agg({
                        'Date': 'count',
                        'Percent_Change': ['mean', 'std', 'min', 'max'],
                        'Range_Percent': ['mean', 'std', 'min', 'max'],
                        'Opening_VIX': 'mean'
                    }).round(2)

                    vol_class_analysis.columns = ['Count', 'Avg_%_Change', 'Std_%_Change', 'Min_%_Change',
                                                  'Max_%_Change',
                                                  'Avg_Range_%', 'Std_Range_%', 'Min_Range_%', 'Max_Range_%',
                                                  'Avg_Opening_VIX']
                    vol_class_analysis = vol_class_analysis.reset_index()
                    vol_class_analysis.to_excel(writer, sheet_name='Volatility_Class_Analysis', index=False)
                    logger.info("Created sheet: Volatility_Class_Analysis")

                # Sheet 4: Day of Week Analysis
                if not df.empty:
                    dow_analysis = df.groupby('Day_of_Week').agg({
                        'Date': 'count',
                        'Percent_Change': ['mean', 'std'],
                        'Range_Percent': ['mean', 'std'],
                        'Opening_VIX': 'mean'
                    }).round(2)

                    dow_analysis.columns = ['Count', 'Avg_%_Change', 'Std_%_Change', 'Avg_Range_%', 'Std_Range_%',
                                            'Avg_Opening_VIX']
                    dow_analysis = dow_analysis.reset_index()
                    dow_analysis.to_excel(writer, sheet_name='Day_of_Week_Analysis', index=False)
                    logger.info("Created sheet: Day_of_Week_Analysis")

                # Sheet 5: Strategy Recommendations
                strategy_recommendations = pd.DataFrame([
                    ['STRATEGY VALIDATION RESULTS', ''],
                    ['', ''],
                    ['Your ATM±2 Strategy Analysis:', ''],
                    ['Days with High Volatility (>=3% range)', f"{stats.get('high_volatility_probability', 0):.1f}%"],
                    ['Expected Success Rate', f"{stats.get('high_volatility_probability', 0):.1f}%"],
                    ['', ''],
                    ['RISK ASSESSMENT', ''],
                    ['Days with Minimal Movement (<0.5%)',
                     f"{(stats.get('minimal_vol_days', 0) / stats.get('total_days', 1) * 100):.1f}%"],
                    ['Days with Extreme Movements (>=5%)',
                     f"{(stats.get('extreme_days', 0) / stats.get('total_days', 1) * 100):.1f}%"],
                    ['', ''],
                    ['OPTIMAL CONDITIONS', ''],
                    ['Best Day of Week', stats.get('best_day', 'N/A')],
                    ['Average Range on Best Day', 'Check Day_of_Week_Analysis sheet'],
                    ['', ''],
                    ['RECOMMENDATIONS', ''],
                    ['1. Strategy Viability',
                     'Moderate to Good' if stats.get('high_volatility_probability', 0) > 25 else 'Poor'],
                    ['2. Risk Level', 'High' if stats.get('extreme_days', 0) > 20 else 'Moderate'],
                    ['3. Best Trading Days', stats.get('best_day', 'N/A')],
                    ['4. Position Sizing', 'Conservative due to volatility'],
                    ['5. Stop Loss', 'Essential - Use tight stops'],
                    ['', ''],
                    ['ADDITIONAL INSIGHTS', ''],
                    ['Average VIX at Open', round(stats.get('avg_opening_vix', 0), 2)],
                    ['Typical 10min Range', f"{round(stats.get('avg_range_percent', 0), 2)}%"],
                    ['Maximum Observed Range', f"{round(stats.get('max_range_percent', 0), 2)}%"]
                ], columns=['Metric', 'Value'])

                strategy_recommendations.to_excel(writer, sheet_name='Strategy_Recommendations', index=False)
                logger.info("Created sheet: Strategy_Recommendations")

            logger.info(f"Excel file saved successfully: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Error saving Excel file: {e}")
            # Fallback to CSV
            csv_filename = f"India_VIX_Analysis_{timestamp}.csv"
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            logger.info(f"Saved as CSV instead: {csv_filename}")
            return csv_filename

    async def run_analysis(self) -> bool:
        """Run complete India VIX analysis"""
        try:
            print("Starting India VIX First 10 Minutes Analysis...")
            print(f"Analyzing last {self.analysis_days} trading days")
            print(f"Focus: 9:15-9:25 AM volatility patterns")

            # Load credentials
            if not await self.load_credentials():
                return False

            # Fetch and analyze data
            if not await self.analyze_all_trading_days():
                print("Failed to fetch sufficient data")
                return False

            # Create analysis DataFrame
            df = self.create_comprehensive_analysis()

            if df.empty:
                print("No data available for analysis")
                return False

            # Calculate statistics
            stats = self.calculate_summary_statistics(df)

            # Save to Excel
            filename = self.save_to_excel(df, stats)

            # Print summary
            self.print_analysis_summary(stats)

            print(f"\nAnalysis completed successfully!")
            print(f"Excel file: {filename}")
            print(f"Total days analyzed: {len(df)}")

            return True

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return False
        finally:
            await self.close_session()

    def print_analysis_summary(self, stats: Dict):
        """Print key analysis summary to console"""
        print("\n" + "=" * 60)
        print("INDIA VIX FIRST 10 MINUTES ANALYSIS SUMMARY")
        print("=" * 60)

        print(f"Total Trading Days: {stats.get('total_days', 0)}")
        print(f"Average Opening VIX: {stats.get('avg_opening_vix', 0):.2f}")
        print(f"Average 10-min Change: {stats.get('avg_percent_change', 0):.2f}%")
        print(f"Average 10-min Range: {stats.get('avg_range_percent', 0):.2f}%")

        print(f"\nSTRATEGY VALIDATION:")
        print(f"High Volatility Days (>=3% range): {stats.get('high_volatility_probability', 0):.1f}%")
        print(f"Extreme Move Days (>=2% change): {stats.get('extreme_move_probability', 0):.1f}%")

        print(f"\nVOLATILITY CLASSIFICATION:")
        print(f"Extreme Days (>=5%): {stats.get('extreme_days', 0)}")
        print(f"High Vol Days (>=3%): {stats.get('high_vol_days', 0)}")
        print(f"Moderate Vol Days (>=1.5%): {stats.get('moderate_vol_days', 0)}")
        print(f"Low Vol Days (>=0.5%): {stats.get('low_vol_days', 0)}")
        print(f"Minimal Vol Days (<0.5%): {stats.get('minimal_vol_days', 0)}")

        print(f"\nDIRECTION ANALYSIS:")
        print(f"Up Days: {stats.get('up_days', 0)}")
        print(f"Down Days: {stats.get('down_days', 0)}")
        print(f"Flat Days: {stats.get('flat_days', 0)}")

        print(f"\nBEST/WORST DAYS:")
        print(f"Best Day of Week: {stats.get('best_day', 'N/A')}")
        print(f"Worst Day of Week: {stats.get('worst_day', 'N/A')}")

        # Strategy recommendation
        high_vol_prob = stats.get('high_volatility_probability', 0)
        if high_vol_prob >= 30:
            recommendation = "GOOD - Strategy has strong potential"
        elif high_vol_prob >= 20:
            recommendation = "MODERATE - Strategy has decent potential"
        else:
            recommendation = "POOR - Strategy has low success probability"

        print(f"\nSTRATEGY RECOMMENDATION: {recommendation}")

    async def close_session(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()


async def main():
    """Main function to run India VIX analysis"""
    print("INDIA VIX FIRST 10 MINUTES VOLATILITY ANALYZER")
    print("Validates your ATM±2 options strategy using historical data")
    print("=" * 60)

    analyzer = IndiaVIXAnalyzer()

    print(f"Analysis Parameters:")
    print(f"- Symbol: India VIX")
    print(f"- Time Period: First 10 minutes (9:15-9:25 AM)")
    print(f"- Historical Days: {analyzer.analysis_days}")
    print(f"- Data Granularity: 1-minute candles")
    print(f"- Output: Excel file with multiple analysis sheets")

    confirm = input(f"\nProceed with analysis? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Analysis cancelled.")
        return

    success = await analyzer.run_analysis()

    if success:
        print("\nAnalysis completed successfully!")
        print("Check the generated Excel file for detailed insights.")
    else:
        print("\nAnalysis failed. Check logs for details.")


if __name__ == "__main__":
    asyncio.run(main())