import os
import numpy as np
import cv2
from PIL import Image


class ORMScanner:
    def __init__(self, math_ans, eng_ans, math_qs_num, eng_qs_num):
        self.math_ans = math_ans
        self.eng_ans = eng_ans
        self.math_qs_num = math_qs_num
        self.eng_qs_num = eng_qs_num
        self.width, self.height = 889, 1280
        self.processed_pages = []

    def preprocess(self, image):
        """Rasmni keyingi bosqichlarga tayyorlash"""

        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        img = cv2.resize(img_cv, (self.width, self.height))
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img, img_gray

    def find_circles(self, img_gray):
        """Rasmdagi doirachalarni topish"""

        img_gray = cv2.medianBlur(img_gray, 5)
        circles = cv2.HoughCircles(
            img_gray,
            cv2.HOUGH_GRADIENT_ALT,
            dp=2,
            minDist=21,
            param1=127,
            param2=0.51,
            minRadius=7,
            maxRadius=19,
        )
        bubbles = []
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for circle in circles[0]:
                x, y, r = circle
                if y < 300 or y > 1300 or x > 800 or x < 110:
                    continue
                elif y > 900 and x > 450:
                    continue
                bubbles.append((x, y, r))
        return bubbles

    def sort_bubbles(self, bubbles, y_tolerance=8):
        """Doirachalarni sortlash"""

        bubbles.sort(key=lambda x: x[1])

        sorted_bubbles = []
        current_row = []

        for bubble in bubbles:
            if not current_row:
                current_row.append(bubble)
            else:
                if abs(bubble[1] - current_row[-1][1]) > y_tolerance:
                    current_row.sort(key=lambda x: x[0])
                    sorted_bubbles.extend(current_row)
                    current_row = [bubble]
                else:
                    current_row.append(bubble)

        if current_row:
            current_row.sort(key=lambda x: x[0])
            sorted_bubbles.extend(current_row)

        return sorted_bubbles

    def split_sections(self, sorted_bubbles):
        """Doirachalarni savollarga bo'lish"""

        all_questions = []
        if not sorted_bubbles:
            return [], []
        current_question = [sorted_bubbles[0]]
        x_gap_threshold = 55

        for i in range(1, len(sorted_bubbles)):
            if abs(sorted_bubbles[i][0] - sorted_bubbles[i - 1][0]) > x_gap_threshold:
                all_questions.append(current_question)
                current_question = [sorted_bubbles[i]]
            else:
                current_question.append(sorted_bubbles[i])

        if current_question:
            all_questions.append(current_question)

        if len(all_questions) == 0:
            return [], []

        math = []
        eng = []

        # Slicing xavfsiz, lekin chegarani dinamik qilish yaxshiroq
        limit = min(80, len(all_questions))
        for i in range(0, limit, 4):
            math.extend(all_questions[i : i + 2])
            eng.extend(all_questions[i + 2 : i + 4])

        if len(all_questions) > 80:
            for i in range(80, len(all_questions)):
                math.append(all_questions[i])

        def split_questions(bubbles):
            cols1, cols2 = [], []
            for i in range(0, len(bubbles), 2):
                cols1.append(bubbles[i])
                # Agar keyingi element mavjud bo'lsa, qo'shamiz
                if i + 1 < len(bubbles):
                    cols2.append(bubbles[i + 1])
            return cols1 + cols2

        math = split_questions(math)
        eng = split_questions(eng)

        return math[: self.math_qs_num], eng[: self.eng_qs_num]

    def get_user_answers(self, math_bubbles, eng_bubbles, gray):
        """Belgilangan doirachalarni topish"""

        def isfilled(gray, x, y, r, threshold=155, inner_ratio=0.65):
            """Bo'yalgan yoki bo'yalmaganligini aniqlaydi"""
            mask = np.zeros(gray.shape[:2], dtype=np.uint8)
            cv2.circle(mask, (x, y), int(r * inner_ratio), 255, -1)
            mean_val = cv2.mean(gray, mask=mask)[0]
            return mean_val < threshold

        def get_filled_options(section, gray):
            """Har bir savol uchun boyalgan variant indeksini qaytaradi (0=A, 1=B, 2=C, 3=D, 4=E)"""
            detected = []
            for question in section:
                filled_idx = []
                if len(question) == 5:
                    for idx, (x, y, r) in enumerate(question):
                        if isfilled(gray, x, y, r, threshold=190, inner_ratio=0.65):
                            filled_idx.append(idx)

                    if len(filled_idx) == 1:
                        detected.append(filled_idx[0])
                    else:
                        detected.append(-1)
                else:
                    detected.append(-1)
            return detected

        math_answers = get_filled_options(math_bubbles, gray)
        eng_answers = get_filled_options(eng_bubbles, gray)
        return math_answers, eng_answers

    # Argumentlar nomini Colabga moslab, tushunarli qildik
    def draw_results(self, img, math_answers, eng_answers, math_coords, eng_coords):
        """Natijalarni rasmga chizish"""

        def draw_circles(img, correct, detected, coords):
            # 'all' o'rniga 'coords' ishlatildi (Python'da 'all' bu maxsus so'z)
            for questions in coords:
                q_idx = coords.index(questions)  # Savolning indeksini olamiz

                # Agar to'g'ri topilgan bo'lsa
                if correct[q_idx] == detected[q_idx]:
                    for idx, (x, y, r) in enumerate(questions):
                        if correct[q_idx] == idx:
                            cv2.circle(img, (x, y), r, (7, 247, 2), -1)

                # Agar xato belgilangan bo'lsa (lekin bo'sh emas)
                elif detected[q_idx] != -1:
                    for idx, (x, y, r) in enumerate(questions):
                        if detected[q_idx] == idx:
                            cv2.circle(
                                img, (x, y), r, (255, 0, 0), 3
                            )  # Belgilangan xato
                        elif correct[q_idx] == idx:
                            cv2.circle(
                                img, (x, y), r, (0, 0, 255), 3
                            )  # Asl to'g'ri javob

                # Agar umuman belgilanmagan bo'lsa
                else:
                    for idx, (x, y, r) in enumerate(questions):
                        if idx == correct[q_idx]:
                            cv2.circle(img, (x, y), r, (0, 0, 255), 3)

        # 1. Matematika uchun chizamiz: To'g'ri kalitlar, User javoblari, Koordinatalar
        draw_circles(img, self.math_ans, math_answers, math_coords)

        # 2. Ingliz tili uchun chizamiz: To'g'ri kalitlar, User javoblari, Koordinatalar
        draw_circles(img, self.eng_ans, eng_answers, eng_coords)

    def calculate_score(self, img, math_answers, eng_answers):
        """Ballni hisoblash"""

        math_score = sum(1 for a, b in zip(math_answers, self.math_ans) if a == b)
        eng_score = sum(1 for a, b in zip(eng_answers, self.eng_ans) if a == b)
        cv2.rectangle(img, (455, 950), (790, 1225), (0, 0, 255), 5)
        cv2.putText(
            img, "Natija:", (550, 1000), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2
        )
        cv2.putText(
            img,
            f"Matematika: {math_score}/{len(math_answers)}",
            (470, 1050),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            img,
            f"Ingiliz tili: {eng_score}/{len(eng_answers)}",
            (470, 1100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            img,
            f"Matem foizi: {int((math_score * 100) / self.math_qs_num)}%",
            (470, 1150),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            img,
            f"Ingiliz foiz: {int((eng_score * 100) / self.eng_qs_num)}%",
            (470, 1200),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
        return math_score, eng_score

    def process(self, img):
        """Rasmni bitta listga to'plash"""

        pil_img = Image.fromarray(img)
        self.processed_pages.append(pil_img)

    def save_results(self, output_folder):
        """Natijalarni saqlash"""
        if self.processed_pages:
            output_path = os.path.join(output_folder, "results.pdf")
            self.processed_pages[0].save(
                output_path, save_all=True, append_images=self.processed_pages[1:]
            )
