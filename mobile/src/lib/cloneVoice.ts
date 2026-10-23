/** Instant Voice Clone languages. Mirror `backend/app/clone_languages.py` and the other client.
 * Record set is Flash v2.5 / Multilingual v2 (32). TTS after clone is Eleven v3.
 */

export type CloneLanguageCode =
  | "ar"
  | "bg"
  | "cs"
  | "da"
  | "de"
  | "el"
  | "en"
  | "es"
  | "fi"
  | "fil"
  | "fr"
  | "hi"
  | "hr"
  | "hu"
  | "id"
  | "it"
  | "ja"
  | "ko"
  | "ms"
  | "nl"
  | "no"
  | "pl"
  | "pt"
  | "ro"
  | "ru"
  | "sk"
  | "sv"
  | "ta"
  | "tr"
  | "uk"
  | "vi"
  | "zh";

export type CloneLanguage = {
  code: CloneLanguageCode;
  /** English name for the picker subtitle. */
  label: string;
  /** Native name shown on chips. */
  nativeLabel: string;
  rtl?: boolean;
  readAloud: string;
};

export const DEFAULT_CLONE_LANGUAGE: CloneLanguageCode = "en";

export const CLONE_LANGUAGES: CloneLanguage[] = [
  {
    code: "en",
    label: "English",
    nativeLabel: "English",
    readAloud: [
      "Hi. Thanks for waiting. I wanted to say this in my own words.",
      "Most days I start slow. Coffee. A window. Then I get into it. If something is off, I say so. If it is good, I say that too.",
      "The order is ready. I will bring it over in five minutes. Wait, can you say that again? I missed the last part.",
      "A few numbers: one, three, five, eight, twelve, twenty, forty. And a few sounds: this, that, those, think, through.",
    ].join("\n\n"),
  },
  {
    code: "ar",
    label: "Arabic",
    nativeLabel: "العربية",
    rtl: true,
    readAloud: [
      "مرحبا. شكرا لانتظارك. أردت أن أقول هذا بكلماتي.",
      "في معظم الأيام أبدأ ببطء. قهوة. نافذة. ثم أبدأ العمل. إذا كان شيء غير مناسب أقوله. وإذا كان جيدا أقوله أيضا.",
      "الطلب جاهز. سأحضره خلال خمس دقائق. انتظر، هل يمكنك أن تعيد ذلك؟ فاتتني الجملة الأخيرة.",
      "بعض الأرقام: واحد، ثلاثة، خمسة، ثمانية، اثنا عشر، عشرون، أربعون. وبعض الأصوات: بيت، ناس، مطر، بحر، شكرا.",
    ].join("\n\n"),
  },
  {
    code: "bg",
    label: "Bulgarian",
    nativeLabel: "Български",
    readAloud: [
      "Здравей. Благодаря, че изчака. Исках да кажа това със свои думи.",
      "Повечето дни започвам бавно. Кафе. Прозорец. После се захващам. Ако нещо не е наред, го казвам. Ако е добре, също го казвам.",
      "Поръчката е готова. Ще я донеса след пет минути. Чакай, можеш ли да повториш? Изпуснах края.",
      "Няколко числа: едно, три, пет, осем, дванадесет, двадесет, четиридесет. И няколко звука: дом, хора, дъжд, море, благодаря.",
    ].join("\n\n"),
  },
  {
    code: "zh",
    label: "Chinese",
    nativeLabel: "中文",
    readAloud: [
      "你好。谢谢你等我。我想用自己的话说这件事。",
      "大多数日子我开始得慢。咖啡。一扇窗。然后进入状态。有不对的地方我会说。好的地方我也会说。",
      "订单好了。五分钟后我送来。等一下，你能再说一遍吗？最后一句我没听清。",
      "几个数字：一、三、五、八、十二、二十、四十。几个声音：家、人、雨、海、谢谢。",
    ].join("\n\n"),
  },
  {
    code: "hr",
    label: "Croatian",
    nativeLabel: "Hrvatski",
    readAloud: [
      "Bok. Hvala što si pričekao. Htio sam to reći svojim riječima.",
      "Većinu dana počinjem sporo. Kava. Prozor. Onda se bacim na posao. Ako nešto nije u redu, kažem. Ako je dobro, i to kažem.",
      "Narudžba je gotova. Donijet ću je za pet minuta. Čekaj, možeš li ponoviti? Promašio sam kraj.",
      "Nekoliko brojeva: jedan, tri, pet, osam, dvanaest, dvadeset, četrdeset. I nekoliko glasova: kuća, ljudi, kiša, more, hvala.",
    ].join("\n\n"),
  },
  {
    code: "cs",
    label: "Czech",
    nativeLabel: "Čeština",
    readAloud: [
      "Ahoj. Díky za čekání. Chtěl jsem to říct vlastními slovy.",
      "Většinu dní začínám pomalu. Káva. Okno. Pak se do toho pustím. Když je něco špatně, řeknu to. Když je to dobré, taky.",
      "Objednávka je hotová. Přinesu ji za pět minut. Počkej, můžeš to zopakovat? Už mi unikl konec.",
      "Pár čísel: jedna, tři, pět, osm, dvanáct, dvacet, čtyřicet. A pár zvuků: dům, lidé, déšť, moře, díky.",
    ].join("\n\n"),
  },
  {
    code: "da",
    label: "Danish",
    nativeLabel: "Dansk",
    readAloud: [
      "Hej. Tak fordi du ventede. Jeg ville sige det med mine egne ord.",
      "De fleste dage starter jeg langsomt. Kaffe. Et vindue. Så går jeg i gang. Hvis noget er galt, siger jeg det. Hvis det er godt, siger jeg det også.",
      "Ordren er klar. Jeg kommer med den om fem minutter. Vent, kan du sige det igen? Jeg missede slutningen.",
      "Et par tal: en, tre, fem, otte, tolv, tyve, fyrre. Og et par lyde: hus, mennesker, regn, hav, tak.",
    ].join("\n\n"),
  },
  {
    code: "nl",
    label: "Dutch",
    nativeLabel: "Nederlands",
    readAloud: [
      "Hoi. Bedankt voor het wachten. Ik wilde dit in mijn eigen woorden zeggen.",
      "De meeste dagen begin ik rustig. Koffie. Een raam. Daarna ga ik erin. Als iets niet klopt, zeg ik dat. Als het goed is, zeg ik dat ook.",
      "De bestelling is klaar. Ik breng hem over vijf minuten. Wacht, kun je dat nog eens zeggen? Ik miste het laatste stuk.",
      "Een paar getallen: een, drie, vijf, acht, twaalf, twintig, veertig. En een paar klanken: huis, mensen, regen, strand, dank je.",
    ].join("\n\n"),
  },
  {
    code: "fil",
    label: "Filipino",
    nativeLabel: "Filipino",
    readAloud: [
      "Kumusta. Salamat sa paghihintay. Gusto kong sabihin ito sa sarili kong salita.",
      "Karamihan ng araw, dahan-dahan akong nagsisimula. Kape. Isang bintana. Tapos, sisimulan ko na. Kung may mali, sinasabi ko. Kung maganda, sinasabi ko rin.",
      "Ready na ang order. Dadalhin ko sa loob ng limang minuto. Sandali, pwedeng ulitin? Hindi ko nakuha ang dulo.",
      "Ilang numero: isa, tatlo, lima, walo, labindalawa, dalawampu, apatnapu. At ilang tunog: bahay, tao, ulan, dagat, salamat.",
    ].join("\n\n"),
  },
  {
    code: "fi",
    label: "Finnish",
    nativeLabel: "Suomi",
    readAloud: [
      "Hei. Kiitos odotuksesta. Halusin sanoa tämän omin sanoin.",
      "Useimmat päivät alkavat hitaasti. Kahvi. Ikkuna. Sitten käyn hommiin. Jos jokin on vialla, sanon sen. Jos on hyvä, sanon senkin.",
      "Tilaus on valmis. Tuon sen viiden minuutin päästä. Odota, voitko toistaa? En kuullut loppua.",
      "Muutama luku: yksi, kolme, viisi, kahdeksan, kaksitoista, kaksikymmentä, neljäkymmentä. Ja muutama ääni: koti, ihmiset, sade, meri, kiitos.",
    ].join("\n\n"),
  },
  {
    code: "fr",
    label: "French",
    nativeLabel: "Français",
    readAloud: [
      "Bonjour. Merci d'avoir attendu. Je voulais dire ça avec mes propres mots.",
      "La plupart des jours, je commence doucement. Un café. Une fenêtre. Ensuite je m'y mets. Si quelque chose cloche, je le dis. Si c'est bien, je le dis aussi.",
      "La commande est prête. Je l'apporte dans cinq minutes. Attends, tu peux répéter ? J'ai raté la fin.",
      "Quelques nombres : un, trois, cinq, huit, douze, vingt, quarante. Et quelques sons : chat, rouge, feuille, cœur, oui.",
    ].join("\n\n"),
  },
  {
    code: "de",
    label: "German",
    nativeLabel: "Deutsch",
    readAloud: [
      "Hallo. Danke fürs Warten. Ich wollte das in meinen eigenen Worten sagen.",
      "Die meisten Tage fange ich langsam an. Kaffee. Ein Fenster. Dann lege ich los. Wenn etwas nicht stimmt, sage ich es. Wenn es gut ist, sage ich das auch.",
      "Die Bestellung ist fertig. Ich bringe sie in fünf Minuten. Warte, kannst du das nochmal sagen? Ich habe den letzten Teil verpasst.",
      "Ein paar Zahlen: eins, drei, fünf, acht, zwölf, zwanzig, vierzig. Und ein paar Laute: ich, ach, schön, über, zwei.",
    ].join("\n\n"),
  },
  {
    code: "el",
    label: "Greek",
    nativeLabel: "Ελληνικά",
    readAloud: [
      "Γεια. Ευχαριστώ που περίμενες. Ήθελα να το πω με δικά μου λόγια.",
      "Τις περισσότερες μέρες ξεκινάω αργά. Καφές. Ένα παράθυρο. Μετά μπαίνω στη δουλειά. Αν κάτι δεν πάει καλά, το λέω. Αν είναι καλό, το λέω κι αυτό.",
      "Η παραγγελία είναι έτοιμη. Θα την φέρω σε πέντε λεπτά. Περίμενε, μπορείς να το ξαναπείς; Έχασα το τέλος.",
      "Μερικοί αριθμοί: ένα, τρία, πέντε, οκτώ, δώδεκα, είκοσι, σαράντα. Και μερικοί ήχοι: σπίτι, άνθρωποι, βροχή, θάλασσα, ευχαριστώ.",
    ].join("\n\n"),
  },
  {
    code: "hi",
    label: "Hindi",
    nativeLabel: "हिन्दी",
    readAloud: [
      "नमस्ते. इंतज़ार के लिए धन्यवाद. मैं यह अपनी बातों में कहना चाहता था.",
      "ज़्यादातर दिन मैं धीरे शुरू करता हूँ. कॉफ़ी. एक खिड़की. फिर काम में लग जाता हूँ. अगर कुछ गलत है, तो कहता हूँ. अगर अच्छा है, तो वो भी कहता हूँ.",
      "ऑर्डर तैयार है. पाँच मिनट में ले आऊँगा. रुकिए, क्या आप दोहरा सकते हैं? आखिरी हिस्सा छूट गया.",
      "कुछ संख्याएँ: एक, तीन, पाँच, आठ, बारह, बीस, चालीस. और कुछ आवाज़ें: घर, लोग, बारिश, समुंदर, धन्यवाद.",
    ].join("\n\n"),
  },
  {
    code: "hu",
    label: "Hungarian",
    nativeLabel: "Magyar",
    readAloud: [
      "Szia. Köszi, hogy vártál. Ezt a saját szavaimmal akartam elmondani.",
      "A legtöbb nap lassan indul. Kávé. Egy ablak. Aztán belevágok. Ha valami nem stimmel, szólok. Ha jó, azt is mondom.",
      "A rendelés kész. Öt perc múlva hozom. Várj, elmondanád még egyszer? A végét nem hallottam.",
      "Néhány szám: egy, három, öt, nyolc, tizenkettő, húsz, negyven. És néhány hang: ház, emberek, eső, tenger, köszönöm.",
    ].join("\n\n"),
  },
  {
    code: "id",
    label: "Indonesian",
    nativeLabel: "Indonesia",
    readAloud: [
      "Hai. Terima kasih sudah menunggu. Aku ingin mengatakannya dengan kata-kataku sendiri.",
      "Kebanyakan hari aku mulai pelan. Kopi. Sebuah jendela. Lalu aku mulai kerja. Kalau ada yang kurang, aku bilang. Kalau bagus, aku bilang juga.",
      "Pesanannya sudah siap. Aku antar dalam lima menit. Tunggu, bisa ulangi? Aku ketinggalan bagian terakhir.",
      "Beberapa angka: satu, tiga, lima, delapan, dua belas, dua puluh, empat puluh. Dan beberapa bunyi: rumah, orang, hujan, pantai, terima kasih.",
    ].join("\n\n"),
  },
  {
    code: "it",
    label: "Italian",
    nativeLabel: "Italiano",
    readAloud: [
      "Ciao. Grazie per l'attesa. Volevo dirlo con le mie parole.",
      "La maggior parte dei giorni inizio piano. Caffè. Una finestra. Poi mi ci metto. Se qualcosa non va, lo dico. Se va bene, lo dico anche.",
      "L'ordine è pronto. Lo porto tra cinque minuti. Aspetta, puoi ripetere? Ho perso l'ultima parte.",
      "Qualche numero: uno, tre, cinque, otto, dodici, venti, quaranta. E qualche suono: casa, gente, pioggia, spiaggia, grazie.",
    ].join("\n\n"),
  },
  {
    code: "ja",
    label: "Japanese",
    nativeLabel: "日本語",
    readAloud: [
      "こんにちは。待ってくれてありがとう。自分の言葉で言いたかったんだ。",
      "たいていの日はゆっくり始まる。コーヒー。窓。それから本腰を入れる。おかしいことがあれば言う。よければそれも言う。",
      "注文の品、できました。五分後に持っていきます。ちょっと待って、もう一回言ってもらえる？最後が聞こえなかった。",
      "数字を少し。いち、さん、ご、はち、じゅうに、にじゅう、よんじゅう。音も少し。いえ、ひと、あめ、うみ、ありがとう。",
    ].join("\n\n"),
  },
  {
    code: "ko",
    label: "Korean",
    nativeLabel: "한국어",
    readAloud: [
      "안녕하세요. 기다려 줘서 고마워요. 제 말로 하고 싶었어요.",
      "대부분의 날은 천천히 시작해요. 커피. 창가. 그다음 일에 들어가요. 이상한 게 있으면 말해요. 좋으면 그것도 말해요.",
      "주문하신 거 나왔어요. 오 분 뒤에 가져갈게요. 잠깐, 다시 말해 줄래요? 마지막을 놓쳤어요.",
      "숫자 몇 개: 하나, 셋, 다섯, 여덟, 열둘, 스물, 마흔. 그리고 소리 몇 개: 집, 사람, 비, 바다, 고마워요.",
    ].join("\n\n"),
  },
  {
    code: "ms",
    label: "Malay",
    nativeLabel: "Melayu",
    readAloud: [
      "Hai. Terima kasih kerana menunggu. Saya mahu katakan ini dengan kata-kata sendiri.",
      "Kebanyakan hari saya mula perlahan. Kopi. Sebuah tingkap. Kemudian saya mula kerja. Kalau ada yang tak kena, saya cakap. Kalau bagus, saya cakap juga.",
      "Pesanan sudah sedia. Saya hantar dalam lima minit. Tunggu, boleh ulang? Saya terlepas bahagian akhir.",
      "Beberapa nombor: satu, tiga, lima, lapan, dua belas, dua puluh, empat puluh. Dan beberapa bunyi: rumah, orang, hujan, laut, terima kasih.",
    ].join("\n\n"),
  },
  {
    code: "no",
    label: "Norwegian",
    nativeLabel: "Norsk",
    readAloud: [
      "Hei. Takk for at du ventet. Jeg ville si dette med mine egne ord.",
      "De fleste dager starter jeg sakte. Kaffe. Et vindu. Så går jeg i gang. Hvis noe er galt, sier jeg det. Hvis det er bra, sier jeg det også.",
      "Bestillingen er klar. Jeg tar den med om fem minutter. Vent, kan du si det igjen? Jeg mistet slutten.",
      "Noen tall: en, tre, fem, åtte, tolv, tjue, førti. Og noen lyder: hus, folk, regn, hav, takk.",
    ].join("\n\n"),
  },
  {
    code: "pl",
    label: "Polish",
    nativeLabel: "Polski",
    readAloud: [
      "Cześć. Dzięki za czekanie. Chciałem powiedzieć to własnymi słowami.",
      "Większość dni zaczynam powoli. Kawa. Okno. Potem biorę się do roboty. Jeśli coś jest nie tak, mówię. Jeśli jest dobrze, też mówię.",
      "Zamówienie jest gotowe. Przyniosę je za pięć minut. Czekaj, możesz powtórzyć? Nie złapałem końca.",
      "Kilka liczb: jeden, trzy, pięć, osiem, dwanaście, dwadzieścia, czterdzieści. I kilka dźwięków: dom, ludzie, deszcz, plaża, dziękuję.",
    ].join("\n\n"),
  },
  {
    code: "pt",
    label: "Portuguese",
    nativeLabel: "Português",
    readAloud: [
      "Oi. Obrigado por esperar. Eu queria dizer isso com as minhas próprias palavras.",
      "Na maioria dos dias eu começo devagar. Café. Uma janela. Depois eu entro no ritmo. Se algo está errado, eu falo. Se está bom, eu falo também.",
      "O pedido está pronto. Eu levo em cinco minutos. Espera, pode repetir? Eu perdi a última parte.",
      "Alguns números: um, três, cinco, oito, doze, vinte, quarenta. E alguns sons: rua, gente, chuva, praia, coração.",
    ].join("\n\n"),
  },
  {
    code: "ro",
    label: "Romanian",
    nativeLabel: "Română",
    readAloud: [
      "Salut. Mulțumesc că ai așteptat. Voiam să spun asta cu cuvintele mele.",
      "În cele mai multe zile încep încet. Cafea. O fereastră. Apoi mă apuc. Dacă ceva nu e în regulă, o spun. Dacă e bine, o spun și pe asta.",
      "Comanda e gata. O aduc în cinci minute. Stai, poți repeta? Am ratat finalul.",
      "Câteva numere: unu, trei, cinci, opt, doisprezece, douăzeci, patruzeci. Și câteva sunete: casă, oameni, ploaie, mare, mulțumesc.",
    ].join("\n\n"),
  },
  {
    code: "ru",
    label: "Russian",
    nativeLabel: "Русский",
    readAloud: [
      "Привет. Спасибо, что подождали. Я хотел сказать это своими словами.",
      "Большинство дней я начинаю медленно. Кофе. Окно. Потом включаюсь. Если что-то не так, я говорю. Если хорошо, тоже говорю.",
      "Заказ готов. Принесу через пять минут. Подождите, можете повторить? Я не расслышал конец.",
      "Несколько чисел: один, три, пять, восемь, двенадцать, двадцать, сорок. И несколько звуков: дом, люди, дождь, море, спасибо.",
    ].join("\n\n"),
  },
  {
    code: "sk",
    label: "Slovak",
    nativeLabel: "Slovenčina",
    readAloud: [
      "Ahoj. Ďakujem, že si počkal. Chcel som to povedať vlastnými slovami.",
      "Väčšinu dní začínam pomaly. Káva. Okno. Potom sa do toho pustím. Ak je niečo zle, poviem to. Ak je to dobré, poviem aj to.",
      "Objednávka je hotová. Prinesiem ju o päť minút. Počkaj, môžeš to zopakovať? Unikol mi koniec.",
      "Pár čísel: jeden, tri, päť, osem, dvanásť, dvadsať, štyridsať. A pár zvukov: dom, ľudia, dážď, more, ďakujem.",
    ].join("\n\n"),
  },
  {
    code: "es",
    label: "Spanish",
    nativeLabel: "Español",
    readAloud: [
      "Hola. Gracias por esperar. Quería decir esto con mis propias palabras.",
      "La mayoría de los días empiezo despacio. Café. Una ventana. Luego me pongo a ello. Si algo no está bien, lo digo. Si está bien, también lo digo.",
      "El pedido está listo. Lo llevo en cinco minutos. Espera, ¿puedes repetir eso? No oí la última parte.",
      "Unos números: uno, tres, cinco, ocho, doce, veinte, cuarenta. Y unos sonidos: casa, gente, lluvia, playa, gracias.",
    ].join("\n\n"),
  },
  {
    code: "sv",
    label: "Swedish",
    nativeLabel: "Svenska",
    readAloud: [
      "Hej. Tack för att du väntade. Jag ville säga det med egna ord.",
      "De flesta dagar börjar jag långsamt. Kaffe. Ett fönster. Sen sätter jag igång. Om något är fel säger jag det. Om det är bra säger jag det också.",
      "Beställningen är klar. Jag tar den om fem minuter. Vänta, kan du säga det igen? Jag missade slutet.",
      "Några tal: ett, tre, fem, åtta, tolv, tjugo, fyrtio. Och några ljud: hus, folk, regn, hav, tack.",
    ].join("\n\n"),
  },
  {
    code: "ta",
    label: "Tamil",
    nativeLabel: "தமிழ்",
    readAloud: [
      "வணக்கம். காத்திருந்ததற்கு நன்றி. இதை என் சொற்களில் சொல்ல விரும்பினேன்.",
      "பெரும்பாலான நாட்களில் மெதுவாகத் தொடங்குவேன். காபி. ஒரு ஜன்னல். பிறகு வேலையில் இறங்குவேன். ஏதாவது தவறாக இருந்தால் சொல்கிறேன். நன்றாக இருந்தால் அதையும் சொல்கிறேன்.",
      "ஆர்டர் தயார். ஐந்து நிமிடத்தில் கொண்டு வருகிறேன். ஒரு நிமிடம், மீண்டும் சொல்ல முடியுமா? கடைசிப் பகுதி தப்பியது.",
      "சில எண்கள்: ஒன்று, மூன்று, ஐந்து, எட்டு, பன்னிரண்டு, இருபது, நாற்பது. சில ஒலிகள்: வீடு, மக்கள், மழை, கடல், நன்றி.",
    ].join("\n\n"),
  },
  {
    code: "tr",
    label: "Turkish",
    nativeLabel: "Türkçe",
    readAloud: [
      "Merhaba. Beklediğin için teşekkürler. Bunu kendi sözlerimle söylemek istedim.",
      "Çoğu gün yavaş başlarım. Kahve. Bir pencere. Sonra işe koyulurum. Bir şey tersse söylerim. İyiysa onu da söylerim.",
      "Sipariş hazır. Beş dakikaya getiririm. Dur, bir daha söyler misin? Son kısmı kaçırdım.",
      "Birkaç sayı: bir, üç, beş, sekiz, on iki, yirmi, kırk. Ve birkaç ses: ev, insan, yağmur, deniz, teşekkürler.",
    ].join("\n\n"),
  },
  {
    code: "uk",
    label: "Ukrainian",
    nativeLabel: "Українська",
    readAloud: [
      "Привіт. Дякую, що зачекали. Я хотів сказати це своїми словами.",
      "Більшість днів я починаю повільно. Кава. Вікно. Потім вмикаюсь. Якщо щось не так, кажу. Якщо добре, теж кажу.",
      "Замовлення готове. Принесу за п'ять хвилин. Зачекайте, можете повторити? Я не розчув кінець.",
      "Кілька чисел: один, три, п'ять, вісім, дванадцять, двадцять, сорок. І кілька звуків: дім, люди, дощ, море, дякую.",
    ].join("\n\n"),
  },
  {
    code: "vi",
    label: "Vietnamese",
    nativeLabel: "Tiếng Việt",
    readAloud: [
      "Xin chào. Cảm ơn đã đợi. Tôi muốn nói điều này bằng lời của mình.",
      "Hầu hết các ngày tôi bắt đầu chậm. Cà phê. Một cửa sổ. Rồi mới vào việc. Nếu có gì không ổn, tôi nói. Nếu tốt, tôi cũng nói.",
      "Đơn đã sẵn sàng. Tôi mang sang trong năm phút. Đợi đã, bạn nói lại được không? Tôi bỏ lỡ phần cuối.",
      "Vài con số: một, ba, năm, tám, mười hai, hai mươi, bốn mươi. Và vài âm: nhà, người, mưa, biển, cảm ơn.",
    ].join("\n\n"),
  },
];

const BY_CODE = new Map(CLONE_LANGUAGES.map((row) => [row.code, row]));
const ALIASES: Record<string, CloneLanguageCode> = {
  tl: "fil",
  nb: "no",
  nn: "no",
  cmn: "zh",
};

export function isCloneLanguageCode(value: string): value is CloneLanguageCode {
  return BY_CODE.has(value as CloneLanguageCode);
}

export function cloneLanguageOf(code?: string | null): CloneLanguage {
  const raw = (code || "").trim().toLowerCase().replace(/_/g, "-");
  const aliased = ALIASES[raw] || raw;
  const key = aliased.split("-")[0] || "";
  const mapped = ALIASES[key] || key;
  return (mapped && BY_CODE.get(mapped as CloneLanguageCode)) || BY_CODE.get("en")!;
}

export function cloneReadAloud(code?: string | null): string {
  return cloneLanguageOf(code).readAloud;
}

export function cloneLanguageLabel(code?: string | null): string | null {
  const raw = (code || "").trim().toLowerCase();
  if (!raw || raw === "multilingual") return null;
  const row = cloneLanguageOf(raw);
  return row.nativeLabel;
}

export function cloneLanguageSelectLabel(row: CloneLanguage): string {
  if (row.code === "en") return row.nativeLabel;
  return `${row.nativeLabel} (${row.label})`;
}
