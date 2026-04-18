from pdf2image import convert_from_path

from .utility import ORMScanner
import pandas as pd
import cv2
from PIL import Image
import os


def check_answer(
    math_answers, eng_answers, math_q_num, eng_q_num, fname, popplerpath, test_num
):
    """Checks answer using ORMScanner class"""
    print("Skanerlash boshlandi...")
    choice_map = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4}
    math_correct = [choice_map[x.lower()] for x in math_answers]
    eng_correct = [choice_map[x.lower()] for x in eng_answers]

    print("PDF-ni rasmga o'tkazish boshlandi...")
    images = convert_from_path(fname, poppler_path=popplerpath)
    print(f"PDF muvaffaqiyatli o'girildi. Sahifalar soni: {len(images)}")
    scanner = ORMScanner(math_correct, eng_correct, math_q_num, eng_q_num)

    eng_results_data = []
    math_results_data = []
    for idx, img in enumerate(images):
        img, gray = scanner.preprocess(img)
        bubbles = scanner.find_circles(gray)
        sorted_bubbles = scanner.sort_bubbles(bubbles)
        math, eng = scanner.split_sections(sorted_bubbles)
        math_answers, eng_answers = scanner.get_user_answers(math, eng, gray)
        scanner.draw_results(img, math_answers, eng_answers, math, eng)
        math_score, eng_score = scanner.calculate_score(img, math_answers, eng_answers)
        scanner.process(img)
        eng_results_data.append(
            {
                "O'quvchi (Sahifa)": f"O'quvchi {idx + 1}",
                f"Test-{test_num}(umumiy {eng_q_num} ta)": eng_score,
                "Foizlarda (%)": int((eng_score * 100) / eng_q_num),
            }
        )
        math_results_data.append(
            {
                "O'quvchi (Sahifa)": f"O'quvchi {idx + 1}",
                f"Test-{test_num}(umumiy {math_q_num} ta)": math_score,
                "Foizlarda (%)": int((math_score * 100) / math_q_num),
            }
        )
    output_folder = "output"
    os.makedirs(output_folder, exist_ok=True)
    scanner.save_results(output_folder)
    if eng_results_data:
        # Papka mavjudligini tekshirish va yaratish
        output_folder = "output"
        os.makedirs(output_folder, exist_ok=True)

        # Keyin saqlash
        excel_path = os.path.join(output_folder, "eng_results.xlsx")
        df = pd.DataFrame(eng_results_data)
        df.to_excel(excel_path, index=False)
        print(
            f"Barcha ingiliz tilin natijalar Excel fayliga muvaffaqiyatli saqlandi: {excel_path}"
        )

    if math_results_data:
        df = pd.DataFrame(math_results_data)
        # Papka mavjudligini tekshirish va yaratish
        output_folder = "output"
        os.makedirs(output_folder, exist_ok=True)

        # Keyin saqlash
        excel_path = os.path.join(output_folder, "math_results.xlsx")
        df.to_excel(excel_path, index=False)
        print(
            f"Barcha  matematika natijalar Excel fayliga muvaffaqiyatli saqlandi: {excel_path}"
        )
