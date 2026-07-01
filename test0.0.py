from pypdf import PdfReader, PdfWriter
import os

merge_mode = False   # True=普通拼接模式，False=自我复制模式
delete_source_files = True   # 仅在普通拼接模式下有效

if merge_mode:
    pdf1_name = input("请输入第一个PDF文件名：").strip()
    pdf2_name = input("请输入第二个PDF文件名：").strip()
    output_name = input("请输入输出PDF文件名：").strip()

    if not pdf1_name.lower().endswith(".pdf"):
        pdf1_name += ".pdf"

    if not pdf2_name.lower().endswith(".pdf"):
        pdf2_name += ".pdf"

    if not output_name.lower().endswith(".pdf"):
        output_name += ".pdf"

    writer = PdfWriter()

    for pdf_name in [pdf1_name, pdf2_name]:
        reader = PdfReader(pdf_name)
        for page in reader.pages:
            writer.add_page(page)

    with open(output_name, "wb") as f:
        writer.write(f)

    if delete_source_files:
        output_abs = os.path.abspath(output_name)
        source_files_abs = {os.path.abspath(pdf1_name), os.path.abspath(pdf2_name)}

        for file_path in source_files_abs:
            if file_path != output_abs:
                os.remove(file_path)

    print("普通拼接完成")

else:
    pdf_name = input("请输入需要自我复制的PDF文件名：").strip()

    if not pdf_name.lower().endswith(".pdf"):
        pdf_name += ".pdf"

    output_name = pdf_name

    reader = PdfReader(pdf_name)
    writer = PdfWriter()

    for _ in range(2):
        for page in reader.pages:
            writer.add_page(page)

    with open(output_name, "wb") as f:
        writer.write(f)

    print("自我复制完成")