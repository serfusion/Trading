import yfinance as yf

def download_gold_data(start_date, end_date):
    try:
        data = yf.download('GC=F', start=start_date, end=end_date, interval='1d')  # Gold futures
        if data.empty:
            print("No data fetched. Please verify the ticker symbol or data availability.")
        else:
            data.to_csv('/home/zven/Gl3/project/T-XAU/data/gold_prices.csv')
            print("Data saved to 'data/gold_prices.csv'")
        return data
    except Exception as e:
        print(f"Error downloading data: {e}")
        return None
    

gold = download_gold_data('2020-01-01', '2023-01-01')
if gold is not None:
    print(gold.head())

def download_test_gold_data(start_date, end_date):
    try:
        data = yf.download('GC=F', start=start_date, end=end_date, interval='1d')  # Gold futures
        if data.empty:
            print("No data fetched. Please verify the ticker symbol or data availability.")
        else:
            data.to_csv('/home/zven/Gl3/project/T-XAU/data/test_gold_prices.csv')
            print("Data saved to 'data/test_gold_prices.csv'")
        return data
    except Exception as e:
        print(f"Error downloading data: {e}")
        return None
gold_test = download_test_gold_data('2023-01-01', '2024-01-01')

