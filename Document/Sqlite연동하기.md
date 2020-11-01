## sqlite 설치하기 
* sqlite 다운로드 페이지로 이동
  * https://www.sqlite.org/download.html 
  * 플랫폼에 맞는 sqlite-tool 다운 받기 
* 다운 받은 tool의 압축을 풀고 sqlite3 실행 후 테이블 생성
```c++
sqlite3.exe <데이터베이스명>.sqlite3
sqlite> create table stockInfo(code, name);
// 종료하려면 .exit 입력
```
* 위와 같이 실행하면 sqlite가 생성된 것을 확인 할 수 있습니다.

### sqlite gui 툴
* https://sqlitebrowser.org/dl/ 다운로드 페이지에서 tool을 설치


## 참고 사이트 
* http://pythonstudy.xyz/python/article/204-SQLite-%EC%82%AC%EC%9A%A9
