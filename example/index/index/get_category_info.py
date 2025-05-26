async def get_category_info(category_name: str=None):
    """獲取指定老師的課程資訊"""
    if not category_name:
        category_name =  "藝能科"  # 預設老師名稱，若未提供則使用此值
    # 初始化 core
    
    from tnfsh_timetable_core import TNFSHTimetableCore
    core = TNFSHTimetableCore()
    index = await core.fetch_index()
    
    # 獲取老師的課程資訊
    category_info = index.index.teacher.data[category_name]
    print(f"分類名稱: {category_name}")
    import json
    print(json.dumps(category_info, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    import asyncio
    asyncio.run(get_category_info("藝能科"))  # 可以替換成其他分類名稱
