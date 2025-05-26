async def get_last_update(target: str = "顏永進"):
    """獲取課表的最後更新時間
    
    Args:
        target: 目標名稱（教師姓名或班級代碼），預設為"顏永進"
    """
    # 初始化 core
    from tnfsh_timetable_core.timetable.crawler import fetch_raw_html, parse_html
    
    # 解析 HTML 獲取最後更新時間
    html = await fetch_raw_html(target)
    last_update = parse_html(html)["last_update"]
    
    print(f"課表最後更新時間: {last_update}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(get_last_update("顏永進"))  # 可以替換成其他教師姓名或班級代碼