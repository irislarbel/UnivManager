from .assignment_handler import AssignmentHandler

class ExamHandler(AssignmentHandler):
    async def extract(self, detail_page, item: dict):
        # 현재는 과제 핸들러와 내부 파싱 로직이 거의 동일하여 상속받은 로직을 바로 사용합니다.
        # 추후 시험/퀴즈만의 특별한 타이머, 비밀번호 등의 추출 로직이 생기면 이 extract를 분리하여 작성합니다.
        
        # AssignmentHandler의 extract 함수 내부에서 "과제 탐색"이라고 출력되는 것을 제외하면
        # 동작 방식이 동일하므로, 시험에 맞는 커스텀 프린트만 추가하고 부모의 로직에 태워도 되지만, 
        # 이 파일이 생성되어 있으므로 언제든 독립적으로 코드를 작성할 수 있습니다.
        print(f"  🚨 [시험/퀴즈 탐색 시작]: {item.get('fullPath')}")
        result = await super().extract(detail_page, item)
        if result:
            result['type'] = '시험/퀴즈'
        return result
