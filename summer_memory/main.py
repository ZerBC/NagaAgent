from extractor_ds_tri import extract_triples
from graph import store_triples
from visualize import visualize_triples
from rag_query_tri import query_knowledge, set_context
import os
import logging
import traceback
import webbrowser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def batch_add_texts(texts): # 批量处理文本，提取三元组并存储
    try:
        all_triples = set()
        for text in texts:
            if not text:
                logger.warning("跳过空文本")
                continue
            logger.info(f"处理文本: {text[:50]}...")
            triples = extract_triples(text)
            if not triples:
                logger.warning(f"文本未提取到三元组: {text}")
            else:
                logger.info(f"提取到三元组: {triples}")
            all_triples.update(triples)
        if not all_triples:
            logger.warning("未提取到任何三元组")
            return False
        logger.info(f"共提取到 {len(all_triples)} 个三元组")
        valid_triples = [
            t for t in all_triples
            if all(t) and all(isinstance(x, str) and x.strip() for x in t)
        ]
        if len(valid_triples) < len(all_triples):
            logger.warning(f"有 {len(all_triples) - len(valid_triples)} 个三元组包含空值，已被过滤")

        if not valid_triples:
            logger.warning("未提取到有效的三元组")
            return False

        store_triples(valid_triples)
        set_context(texts)  # 设置查询上下文
        return True
    except Exception as e:
        logger.error(f"批量处理文本失败: {e}")
        return False

def batch_add_from_file(filename): # 从文件批量处理文本
    try:
        if not os.path.exists(filename):
            logger.error(f"文件 {filename} 不存在")
            raise FileNotFoundError(f"文件 {filename} 不存在")
        with open(filename, 'r', encoding='utf-8') as f:
            texts = [line.strip() for line in f if line.strip()]
        if not texts:
            logger.warning(f"文件 {filename} 为空")
            return False
        logger.info(f"从文件 {filename} 读取 {len(texts)} 条文本")
        return batch_add_texts(texts)


    except Exception as e:
        logger.error(f"批量处理文本失败: {e}")
        traceback.print_exc()  # 打印完整错误堆栈信息
        return False


def main(): # 主程序
    try:
        print("请选择输入方式：")
        print("1 - 手动输入文本")
        print("2 - 从文件读取文本")
        choice = input("请输入 1 或 2：").strip()

        if choice == "1":
            print("请输入要处理的文本（每行一段，输入空行结束）：")
            texts = []
            while True:
                text = input("> ")
                if not text.strip():
                    break
                texts.append(text.strip())

            if not texts:
                print("未输入任何文本，使用默认测试文本。")
                texts = [
                    "你好，我是娜迦。"
                ]

            success = batch_add_texts(texts)

        elif choice == "2":
            filename = input("请输入文件路径：").strip()
            success = batch_add_from_file(filename)

        else:
            print("无效输入，仅支持 1 或 2。程序退出。")
            return

        if success:
            webbrowser.open("graph.html")
            print("\n知识图谱已生成：graph.html")
            print("请输入查询问题（输入空行退出）：")
            while True:
                query = input("> ")
                if not query.strip():
                    print("退出查询。")
                    break
                result = query_knowledge(query)
                print("\n查询结果：")
                print(result)
                print("\n请输入下一个查询问题（输入空行退出）：")
        else:
            print("文本处理失败，请检查控制台日志。")

    except KeyboardInterrupt:
        logger.info("用户中断程序")
        print("\n程序已中断。")
    except Exception as e:
        logger.error(f"主程序运行失败: {e}")
        print(f"发生错误：{e}")


if __name__ == '__main__':
    main()