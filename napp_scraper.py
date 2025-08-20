import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup, Tag
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

# --- 実行時定数 ---
TIMEOUT_SEC = 20
SLEEP_SHORT = 1.5
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# --- 設定情報（環境変数から読み込み） ---
CAMPSITE_ID = os.environ["NAP_CAMPSITE_ID"]
STAFF_ID = os.environ["NAP_STAFF_ID"]
PASSWORD = os.environ["NAP_PASSWORD"]
LOGIN_URL = "https://adm.nap-camp.com/campsite/"
RESERVATION_LIST_URL = (
    "https://adm.nap-camp.com/admin/campsite/reservation_list/index/list?tabId=1"
)

# --- 出力先（リポジトリ内 data/ 配下） ---
JST = timezone(timedelta(hours=9))
today_str = datetime.now(JST).strftime("%Y-%m-%d")
output_dir = Path("data")
output_dir.mkdir(parents=True, exist_ok=True)
OUTPUT_CSV = output_dir / f"napp_reservation_data_{today_str}.csv"


# --- WebDriverの初期設定 ---
def setup_driver():
    options = Options()
    options.add_argument(f"--user-agent={USER_AGENT}")
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=ja")
    options.add_argument("--force-device-scale-factor=1")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_window_size(1600, 900)
    return driver


# --- ログイン関数 ---
def login(driver):
    print("ログインページにアクセスします...")
    driver.get(LOGIN_URL)
    WebDriverWait(driver, TIMEOUT_SEC).until(
        EC.presence_of_element_located((By.NAME, "campsite_id"))
    )
    time.sleep(SLEEP_SHORT)

    print("ログイン情報を入力します...")
    driver.find_element(By.NAME, "campsite_id").send_keys(CAMPSITE_ID)
    driver.find_element(By.NAME, "campsite_op_id").send_keys(STAFF_ID)
    driver.find_element(By.NAME, "campsite_op_pwd").send_keys(PASSWORD)
    driver.find_element(By.XPATH, "//button[@submit_not_twice='']").click()
    print("ログインボタンをクリックしました。")

    WebDriverWait(driver, TIMEOUT_SEC).until(EC.url_contains("top.php"))
    if "top.php" in driver.current_url:
        print("ログインに成功しました！")
    else:
        print("ログインに失敗した可能性があります。")
        driver.quit()
        raise Exception("ログインに失敗しました。")


# --- メイン処理 ---
if __name__ == "__main__":
    driver = None
    all_reservation_data = []

    try:
        driver = setup_driver()
        login(driver)
        driver.get(RESERVATION_LIST_URL)
        WebDriverWait(driver, TIMEOUT_SEC).until(
            EC.presence_of_element_located((By.CLASS_NAME, "listTitle"))
        )
        time.sleep(SLEEP_SHORT)

        current_page_num = 1
        while True:
            print(f"現在のページ ({current_page_num}) から予約情報を抽出します...")
            soup = BeautifulSoup(driver.page_source, "html.parser")
            reservation_table = soup.find("table", class_="table")

            if reservation_table is None:
                print(
                    "予約テーブルが見つかりませんでした。ページの読み込み待機を延長します。"
                )
                time.sleep(3)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                reservation_table = soup.find("table", class_="table")
                if reservation_table is None:
                    print(
                        "依然として予約テーブルが見つからないため、このページの解析をスキップします。"
                    )
                    break

            if isinstance(reservation_table, Tag):
                tbody = reservation_table.find("tbody")
                if isinstance(tbody, Tag):
                    rows = tbody.find_all("tr")
                    for row in rows:
                        if isinstance(row, Tag):
                            cols = row.find_all("td")
                            if cols and len(cols) > 13:
                                reservation = {}
                                reservation["予約ID"] = cols[1].get_text(strip=True)
                                reservation["予約状況"] = cols[2].get_text(strip=True)
                                reservation["予約日時"] = cols[3].get_text(strip=True)
                                reservation["代表者氏名"] = cols[4].get_text(strip=True)
                                reservation["チェックイン"] = cols[5].get_text(
                                    strip=True
                                )
                                reservation["チェックアウト"] = cols[6].get_text(
                                    strip=True
                                )
                                reservation["予約プラン名"] = cols[7].get_text(
                                    strip=True
                                )
                                reservation["利用人数"] = cols[8].get_text(
                                    separator=" ", strip=True
                                )
                                reservation["施設利用料"] = cols[9].get_text(strip=True)
                                reservation["施設過去来場回数"] = cols[10].get_text(
                                    strip=True
                                )
                                phone_number = cols[11].get_text(strip=True)
                                reservation["電話番号"] = f'="{phone_number}"'
                                reservation["メールアドレス"] = cols[12].get_text(
                                    strip=True
                                )
                                reservation["住所"] = cols[13].get_text(strip=True)
                                all_reservation_data.append(reservation)

            try:
                next_button = WebDriverWait(driver, TIMEOUT_SEC).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[@aria-label='Go to next page']")
                    )
                )
                class_attr = next_button.get_attribute("class")
                if class_attr is not None and "Mui-disabled" in class_attr:
                    print("最後のページに到達しました。")
                    break
                print("次のページへ移動します...")
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(SLEEP_SHORT)
                WebDriverWait(driver, TIMEOUT_SEC).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "listTitle"))
                )
                current_page_num += 1
            except (
                NoSuchElementException,
                TimeoutException,
                ElementClickInterceptedException,
            ):
                print("次のページボタンが見つかりませんでした。処理を終了します。")
                break

    except Exception as e:
        print(f"スクレイピング中にエラーが発生しました: {e}")
    finally:
        if all_reservation_data:
            column_order = [
                "予約ID",
                "予約状況",
                "予約日時",
                "代表者氏名",
                "チェックイン",
                "チェックアウト",
                "予約プラン名",
                "利用人数",
                "施設利用料",
                "施設過去来場回数",
                "電話番号",
                "メールアドレス",
                "住所",
            ]
            df = pd.DataFrame(all_reservation_data, columns=column_order)
            try:
                df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
                print(
                    f"全{len(all_reservation_data)}件の予約情報を '{OUTPUT_CSV}' に保存しました。"
                )
            except Exception as csv_e:
                print(f"CSVファイルの保存中にエラーが発生しました: {csv_e}")
        else:
            print("取得できる予約情報がありませんでした。")

        if driver:
            print("ブラウザを閉じます。")
            driver.quit()
