async def get_class_info(class_code: str=None):
    """獲取指定班級的課程資訊
    
    Args:
        class_code: 班級代碼（如: "307"），若未提供則預設為"307"
    """
    if not class_code:
        class_code = "307"  # 預設班級代碼
    
    # 初始化 core
    from tnfsh_timetable_core import TNFSHTimetableCore
    core = TNFSHTimetableCore()
    index = await core.fetch_index()
    
    # 獲取班級的課程資訊
    class_info = index.reverse_index.root[class_code]
    print(f"班級: {class_code}")
    print(class_info.model_dump_json(indent=4))

if __name__ == "__main__":
    import asyncio
    asyncio.run(get_class_info("307"))  # 可以替換成其他班級代碼