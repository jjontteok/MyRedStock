from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from send_briefing import render_briefing_page


stocks = [
    "\uc0bc\uc131\uc804\uc790",
    "LG\uc804\uc790",
    "SK\ud558\uc774\ub2c9\uc2a4",
    "\uc0bc\uc131\uc804\uae30",
]

briefing = "\n\n".join(
    [
        "AI \ubc18\ub3c4\uccb4\uc640 \ub85c\ubd07 \uae30\ub300\uac10\uc774 \ud575\uc2ec\uc785\ub2c8\ub2e4. \uc0bc\uc131\uc804\uc790\ub294 \ub178\uc0ac \ub9ac\uc2a4\ud06c \uc644\ud654, LG\uc804\uc790\ub294 \ub85c\ubd07\u00b7\ud53c\uc9c0\uceecAI \uae30\ub300, SK\ud558\uc774\ub2c9\uc2a4\ub294 HBM \uc218\uc694 \uac15\uc138\uac00 \uc8fc\uc694 \ud3ec\uc778\ud2b8\uc785\ub2c8\ub2e4.",
        "\uc0bc\uc131\uc804\uc790: \uc784\ub2e8\ud611 \uc7a0\uc815\ud569\uc758\uc548 \uac00\uacb0\ub85c \ud30c\uc5c5 \ub9ac\uc2a4\ud06c\ub294 \uc644\ud654\ub410\uc2b5\ub2c8\ub2e4. DS \ud2b9\ubcc4\uc131\uacfc\uae09 \uc2e0\uc124\uc740 \uc9c1\uc6d0 \ubcf4\uc0c1 \uce21\uba74\uc5d0\uc11c \uae0d\uc815\uc801\uc774\ub098 \ube44\uc6a9 \ubd80\ub2f4\uacfc HBM4 \uacf5\uae09 \ud655\ub300 \uc18d\ub3c4\ub294 \uacc4\uc18d \ud655\uc778\ud574\uc57c \ud569\ub2c8\ub2e4.",
        "LG\uc804\uc790: \ub85c\ubd07\uacfc \ud53c\uc9c0\uceecAI \uae30\ub300\uac00 \uc8fc\uac00 \ubaa8\uba58\ud140\uc73c\ub85c \uc791\uc6a9\ud588\uc2b5\ub2c8\ub2e4. \uc5d4\ube44\ub514\uc544 \ud611\ub825 \uae30\ub300\uac00 \ubd80\uac01\ub410\uc9c0\ub9cc, \ub2e8\uae30 \uae09\ub4f1 \uc774\ud6c4 \ucc28\uc775\uc2e4\ud604 \uac00\ub2a5\uc131\uc740 \ud568\uaed8 \ubd10\uc57c \ud569\ub2c8\ub2e4.",
        "SK\ud558\uc774\ub2c9\uc2a4: HBM\uacfc AI \uc11c\ubc84 \uba54\ubaa8\ub9ac \uc218\uc694 \uac15\uc138\uac00 \ud575\uc2ec\uc785\ub2c8\ub2e4. \uc99d\uad8c\uac00 \ubaa9\ud45c\uac00 \uc0c1\ud5a5\uacfc \uc5d4\ube44\ub514\uc544\ud5a5 \uacf5\uae09 \ud655\ub300 \uae30\ub300\ub294 \uae0d\uc815 \uc7ac\ub8cc\uc785\ub2c8\ub2e4.",
        "\uc624\ub298 \uccb4\ud06c: AI/HBM \ubc38\ub958\uccb4\uc778 \ub274\uc2a4, LG\uadf8\ub8f9\uc8fc \uae09\ub4f1 \ud6c4 \uc218\uae09, \ucf54\uc2a4\ud53c\u00b7\ud658\uc728\u00b7\ubbf8\uad6d \uae30\uc220\uc8fc \ud750\ub984\uc744 \ud568\uaed8 \ud655\uc778\ud558\uc138\uc694.",
    ]
)

articles = [
    {
        "stock": "\uc0bc\uc131\uc804\uc790",
        "title": "\uc0bc\uc131\uc804\uc790 \uc784\ub2e8\ud611 \uc7a0\uc815\ud569\uc758\uc548 \uac00\uacb0",
        "link": "https://www.ajunews.com/view/20260527105646186",
        "published": "\uc544\uc8fc\uacbd\uc81c",
    },
    {
        "stock": "LG\uc804\uc790",
        "title": "LG\uc804\uc790 \ub85c\ubd07\u00b7AI \uae30\ub300\uac10 \ubd80\uac01",
        "link": "https://biz.chosun.com/stock/stock_general/2026/05/25/3SYW3HXI2VHPBP5X22TFCHRB5Q/",
        "published": "\uc870\uc120\ube44\uc988",
    },
    {
        "stock": "LG\uc804\uc790",
        "title": "LG\uc804\uc790 \uae09\ub4f1\uacfc \uc5d4\ube44\ub514\uc544 \ud611\ub825 \uae30\ub300",
        "link": "https://www.fnnews.com/ampNews/202605291605059782",
        "published": "\ud30c\uc774\ub0b8\uc15c\ub274\uc2a4",
    },
    {
        "stock": "SK\ud558\uc774\ub2c9\uc2a4",
        "title": "SK\ud558\uc774\ub2c9\uc2a4 \ubaa9\ud45c\uac00 \uc0c1\ud5a5",
        "link": "https://www.newspim.com/news/view/20260529000100",
        "published": "\ub274\uc2a4\ud54c",
    },
    {
        "stock": "SK\ud558\uc774\ub2c9\uc2a4",
        "title": "SK\ud558\uc774\ub2c9\uc2a4 \uc5d4\ube44\ub514\uc544\ud5a5 \uba54\ubaa8\ub9ac \uacf5\uae09 \uae30\ub300",
        "link": "https://biz.chosun.com/it-science/ict/2026/05/15/BPKV5SD7DND2BONRXLWG4AQEMQ/",
        "published": "\uc870\uc120\ube44\uc988",
    },
]

page = render_briefing_page(stocks, articles, briefing)
Path("docs").mkdir(exist_ok=True)
Path("docs/briefings").mkdir(parents=True, exist_ok=True)
Path("docs/index.html").write_text(page, encoding="utf-8")
Path("docs/briefings/2026-05-31.html").write_text(page, encoding="utf-8")
