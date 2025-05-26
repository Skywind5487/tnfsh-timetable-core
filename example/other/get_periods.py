async def get_periods(target: str = "顏永進"):
    """獲取課程節次資訊"""
    # 初始化 core
    from tnfsh_timetable_core.timetable.crawler import fetch_raw_html, parse_html
      # 確保網頁已被抓取

    # 解析 HTML 獲取課程節次資訊
    html = await fetch_raw_html(target)
    print(type(html))
    periods = parse_html(html)["periods"]

    print("課程節次資訊:")
    for period_name, time_info in periods.items():
        print(f"節次: {period_name}, 時間: {time_info[0]} - {time_info[1]}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(get_periods("顏永進"))  # 獲取課程節次資訊