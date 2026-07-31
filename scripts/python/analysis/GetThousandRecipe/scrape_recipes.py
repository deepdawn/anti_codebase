import os
import sys
import time
import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# teams_email_mcp.py 모듈 경로 추가
utils_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'utils'))
sys.path.append(utils_path)
from teams_email_mcp import send_email  # type: ignore

# Parameters
KEYWORDS = ["한식", "중식", "일식", "양식"]
TARGET_COUNT = 150
CREDENTIALS_FILE = "/Users/galaxy.jang/anti_codebase/.etc/galaxy-test-41bbc-a27b358c8670.json"
SPREADSHEET_ID = "11X7LxqcFjL_Dvd7GzOjY2M-Urwc5wmgVMkXVPkTOPZU"
SHEET_NAME = "sheet2"
BASE_URL = "https://www.10000recipe.com"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_recipe_links(keyword, target_count):
    links = []
    page = 1
    while len(links) < target_count:
        url = f"{BASE_URL}/recipe/list.html?q={keyword}&order=reco&page={page}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching list page {page} for {keyword}: {e}")
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 만개의 레시피 리스트 아이템 선택자
        items = soup.select('.common_sp_link')
        if not items:
            break
            
        for item in items:
            link = item.get('href')
            if link and link.startswith('/recipe/'):
                links.append(BASE_URL + link)
                if len(links) >= target_count:
                    break
        page += 1
        time.sleep(1) # IP 차단 방지
    return links

def parse_recipe_detail(url, category):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 요리 이름
        title_elem = soup.select_one('.view2_summary h3')
        name = title_elem.text.strip() if title_elem else "N/A"
        
        # 2. 재료
        ingredients = []
        ingre_elems = soup.select('#divConfirmedMaterialArea li')
        for el in ingre_elems:
            ing_name = el.select_one('.ingre_list_name')
            ing_amt = el.select_one('.ingre_list_ea')
            
            # 재료명과 수량 조합
            name_text = ing_name.text.strip() if ing_name else ""
            amt_text = ing_amt.text.strip() if ing_amt else ""
            
            if name_text and amt_text:
                ingredients.append(f"{name_text} {amt_text}")
            elif name_text:
                ingredients.append(name_text)
                
        ingredients_str = ", ".join(ingredients) if ingredients else "N/A"
        
        # 3. 상세 레시피
        steps = []
        step_elems = soup.select('.view_step_cont .media-body')
        for i, step in enumerate(step_elems, 1):
            steps.append(f"{i}. {step.text.strip()}")
        recipe_str = "\n".join(steps) if steps else "N/A"
        
        # 4. 이미지 URL
        img_elem = soup.select_one('#main_thumbs')
        img_url = img_elem.get('src') if img_elem else "N/A"
        
        return {
            "카테고리": category,
            "요리 이름": name,
            "레시피 필요 재료": ingredients_str,
            "상세 레시피": recipe_str,
            "레시피 링크": url,
            "이미지URL": img_url
        }
    except Exception as e:
        print(f"Error parsing detail {url}: {e}")
        return None

def main():
    all_recipes = []
    
    for keyword in KEYWORDS:
        print(f"\n--- [{keyword}] 상위 {TARGET_COUNT}개 레시피 링크 수집 중 ---")
        links = get_recipe_links(keyword, TARGET_COUNT)
        print(f"[{keyword}] {len(links)}개 링크 수집 완료. 상세 데이터 추출 시작...")
        
        for i, link in enumerate(links, 1):
            print(f"  [{keyword}] {i}/{len(links)} 추출 중: {link}")
            detail = parse_recipe_detail(link, keyword)
            if detail:
                all_recipes.append(detail)
            time.sleep(0.5) # IP 차단 방지
            
    # 결과를 로컬 CSV로 저장 (백업용)
    out_dir = "/Users/galaxy.jang/anti_codebase/results/data_extract/GetThousandRecipe"
    os.makedirs(out_dir, exist_ok=True)
    df = pd.DataFrame(all_recipes)
    csv_path = os.path.join(out_dir, "recipes_backup.csv")
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n로컬 백업 저장 완료: {csv_path}")
    
    # 구글 스프레드시트 업데이트
    print("\n구글 스프레드시트 업데이트 시작...")
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        
        # A2:F 범위 기존 데이터 삭제
        sheet.batch_clear(["A2:F"])
        
        # 데이터 업데이트
        data_to_update = df.values.tolist()
        if data_to_update:
            try:
                sheet.update(range_name='A2', values=data_to_update)
            except TypeError:
                # gspread 버전에 따른 호환성
                sheet.update('A2', data_to_update)
            print("구글 스프레드시트 업데이트 완료.")
    except Exception as e:
        print(f"구글 스프레드시트 업데이트 중 오류 발생: {e}")
        
    # Teams 이메일 알림 전송
    print("\nTeams 완료 알림 전송 중...")
    try:
        subject = f"레시피 스크래핑 파이프라인 완료 ({len(all_recipes)}건)"
        body = (f"GetThousandRecipe 프로젝트 스크래핑이 완료되었습니다.\n\n"
                f"- 총 수집 건수: {len(all_recipes)}건\n"
                f"- 구글 시트 반영 범위: {SHEET_NAME}!A2:F\n"
                f"- 로컬 백업 경로: {csv_path}\n\n"
                f"작업을 성공적으로 마쳤습니다.")
        
        response = send_email(subject, body, csv_path)
        print("Teams 알림 응답:", response)
    except Exception as e:
        print(f"Teams 알림 전송 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
