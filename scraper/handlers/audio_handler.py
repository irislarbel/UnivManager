from .base_handler import BaseHandler
import os
import re

class AudioHandler(BaseHandler):
    async def extract(self, detail_page, item: dict, save_dir: str = None):
        full_path = item.get('fullPath', '')
        href = item.get('href', '#')
        scraper_id = item.get('scraperId')
        item_title = item.get('title', '제목없음')
        
        print(f"  🎵 [오디오 다운로드 시도]: {full_path}")
        
        download_status = "not_downloadable"
        downloaded_info = None
        
        # 1. 1차 시도: 더보기 메뉴에 일반 다운로드 버튼이 있는 경우 대비
        if scraper_id and save_dir:
            download_result = await self.download_file(detail_page, scraper_id, save_dir)
            if download_result:
                download_status = download_result.get('status', 'not_downloadable')
                if download_status == "success":
                    downloaded_info = download_result
                    href = downloaded_info.get('url', href)
                    
        # 2. 2차 시도: 다운로드 메뉴가 없거나 실패 시, 내장 뷰어(오디오 플레이어) 추출
        if download_status in ["not_downloadable", "failed"] and scraper_id and save_dir:
            print("    🎧 더보기 메뉴 다운로드 불가. 패널을 열어 내장 오디오 소스를 직접 추출합니다.")
            opened = await self.open_panel_if_needed(detail_page, scraper_id)
            if opened:
                try:
                    # 패널 오픈 후 HTML5 <audio><source src="..."></audio> 렌더링 대기
                    audio_source_selector = 'audio source'
                    source_el = await detail_page.wait_for_selector(audio_source_selector, timeout=5000, state="attached")
                    
                    if source_el:
                        src_url = await source_el.get_attribute('src')
                        if src_url:
                            # 상대 경로를 블랙보드 도메인 절대 경로로 변환
                            if src_url.startswith('/'):
                                src_url = "https://eclass2.ajou.ac.kr" + src_url
                                
                            print(f"    📡 [오디오 소스 감지 완료]: {src_url}")
                            
                            # Playwright APIContext를 이용하여 브라우저(로그인된 쿠키) 상태로 파일 바이트 다운로드
                            response = await detail_page.context.request.get(src_url)
                            if response.ok:
                                clean_title = re.sub(r'[\\/:*?"<>|]', '_', item_title)
                                # 확장자 mp3 강제 부여 (사용자 요구사항: MP3 전담)
                                if not clean_title.lower().endswith('.mp3'):
                                    filename = f"{clean_title}.mp3"
                                else:
                                    filename = clean_title
                                    
                                final_filepath = os.path.join(save_dir, filename)
                                os.makedirs(save_dir, exist_ok=True)
                                
                                with open(final_filepath, 'wb') as f:
                                    f.write(await response.body())
                                    
                                print(f"      ✅ [내장 오디오 다운로드 최종 성공]: {filename}")
                                downloaded_info = {'filename': filename, 'url': src_url}
                                download_status = "success"
                                href = src_url
                            else:
                                print(f"      ⚠️ 내장 오디오 데이터 수신 실패 (HTTP 상태 코드: {response.status})")
                                download_status = "failed"
                except Exception as e:
                    print(f"    ℹ️ 패널 내부에서 오디오 태그(<audio>)를 찾지 못했습니다: {e}")
                
                # 추출이 끝났으므로 화면 잔존 방지를 위해 패널 닫기 (필수)
                await self.close_all_panels(detail_page)
                
        return {
            "type": "오디오",
            "title": item_title,
            "href": href,
            "downloaded_file": downloaded_info.get('filename') if downloaded_info else None,
            "download_status": download_status
        }
