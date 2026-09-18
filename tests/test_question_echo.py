"""The model handing the question back instead of answering it.

Found by pointing the mobile client at the running service and asking a price
question: "vệ sinh máy lạnh bao nhiêu tiền" came back as "Vệ sinh máy lạnh bao
nhiêu tiền?" — three times out of three, so not a sampling accident.

The existing stripper could not see it. That one removes the *labelled* echo,
"Khách: <question>" followed by "Trả lời dựa trên tài liệu trên:", and this form
carries no label to strip. It is the same defect wearing no frame.

A customer reading their own words back does not get an answer and does get the
impression that nobody is listening, so an echo is treated as a failed
generation: the caller already falls back to the retrieved passages, which is
clumsier prose carrying the right content.
"""

from app.services.pipeline.qwen_client import _is_the_question_again


class TestAnEchoIsRecognised:
    def test_the_exact_case_seen_on_the_running_service(self):
        assert _is_the_question_again(
            "Vệ sinh máy lạnh bao nhiêu tiền?",
            "vệ sinh máy lạnh bao nhiêu tiền",
        )

    def test_case_and_punctuation_do_not_hide_it(self):
        assert _is_the_question_again(
            "BẢO HÀNH BAO LÂU???",
            "bảo hành bao lâu",
        )

    def test_a_shorter_fragment_of_the_question_is_still_an_echo(self):
        assert _is_the_question_again("máy giặt không vắt", "máy giặt không vắt ạ")

    def test_reordered_words_from_the_question_are_still_an_echo(self):
        assert _is_the_question_again("Bao lâu bảo hành?", "bảo hành bao lâu")


class TestARealAnswerSurvives:
    def test_an_answer_that_repeats_the_question_then_explains_is_kept(self):
        assert not _is_the_question_again(
            "Dạ vệ sinh máy lạnh bao nhiêu tiền thì tuỳ công suất ạ, "
            "máy 1HP là 150.000đ, máy 2HP là 200.000đ nhé anh/chị.",
            "vệ sinh máy lạnh bao nhiêu tiền",
        )

    def test_a_short_but_genuine_answer_is_kept(self):
        assert not _is_the_question_again("Dạ 30 ngày ạ.", "bảo hành bao lâu")

    def test_a_one_word_answer_the_question_did_not_contain_is_kept(self):
        assert not _is_the_question_again("Được ạ.", "có sửa tại nhà không")

    def test_the_guard_needs_something_on_both_sides(self):
        assert not _is_the_question_again("", "bảo hành bao lâu")
        assert not _is_the_question_again("Dạ 30 ngày ạ.", "")
        assert not _is_the_question_again("...", "bảo hành bao lâu")


class TestItDoesNotFoldDiacritics:
    """The folding-collision family has cost this pipeline five bugs.

    Nothing here needs it: both sides are Vietnamese written the same way. These
    pin that two different words are not treated as one just because they agree
    once the accents are gone.
    """

    def test_gia_and_giat_are_not_the_same_word(self):
        assert not _is_the_question_again("Giá ạ?", "máy giặt")

    def test_an_answer_about_a_dryer_is_not_an_echo_of_a_washer_question(self):
        assert not _is_the_question_again("Máy sấy ạ", "máy giặt")
