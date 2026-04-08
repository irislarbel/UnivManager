import asyncio
import schedule
import time

from scraper.blackboard_scraper import BlackboardScraper
from analyzer.multimedia_analyzer import MultimediaAnalyzer
from analyzer.document_analyzer import DocumentAnalyzer

class UnivManagerApp:
    def __init__(self):
        self.scraper = BlackboardScraper()
        self.multimedia_analyzer = MultimediaAnalyzer()
        self.document_analyzer = DocumentAnalyzer()

    async def process_new_items(self):
        """새로운 항목을 발견하고 분석(다운로드, 파싱) 및 저장 처리"""
        print("\n--- 유니브매니저 데이터 수집 프로세스 시작 ---")
        
        # 1. Blackboard 스크래핑 실행
        # scraper.run()에서 실제 신규 발견 리스트(영상, 공지 등)를 반환하도록 향후 보완
        await self.scraper.run()
        
        # TODO: 스크래핑된 항목을 구글 드라이브 트리에 맞춰 업로드하고,
        # Gemini 3 Pro를 통해 강의록을 생성한 뒤 ChromaDB에 삽입하는 로직 구현
        
        print("--- 유니브매니저 데이터 수집 프로세스 종료 ---\n")

    def run_scheduler(self):
        """1시간마다 새로운 강의자료/영상 체크"""
        print("스케줄러 시작. 1시간 주기로 데이터 수집을 실행합니다...")
        schedule.every(1).hours.do(lambda: asyncio.run(self.process_new_items()))

        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    app = UnivManagerApp()
    # 즉시 한 번 실행
    asyncio.run(app.process_new_items())
    # 이후 스케줄러 작동
    app.run_scheduler()
