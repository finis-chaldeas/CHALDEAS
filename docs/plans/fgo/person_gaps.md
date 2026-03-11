# FGO 서번트 — 인물 DB 매칭 현황 리스트

생성일: 2026-03-10

> **⚠️ 주의 (2026-03-10 재분석):** 이 문서는 링크 82건 시점에 작성됨.
> 현재 실제 상태는 **389/449 링크 완료 (87%)**, 배치 삽입 142명 포함.
> 아래 수치는 과거 기준이며, 실제 잔여 작업은 `person_link_research.md` 참조.
> - 오매칭 수정 필요: ~21건
> - 신규 인물 생성 필요: ~18명
> - 미링크 60명 = 대부분 Fate 오리지널 (링크 불필요)

## 요약 (초기 분석 — 과거 기준)

| 상태 | 수 |
|------|-----|
| 확인 완료 (DB 반영 가능) | 121 |
| 미등재 (전설) | 48 |
| 미등재 (신화) | 54 |
| 미등재 (역사, DB에 없음) | 17 |
| 미등재 (가공) | 9 |
| FGO 오리지널 | 23 |
| 미분류 (DB 매치 있음) | 38 |
| 미분류 (DB에 없음) | 112 |

---

## 1. 즉시 링킹 가능 (DB 매치 있음, 38명)

persons 테이블에 매칭 인물이 있지만 아직 연결 안 됨. link_fgo_persons.py에 추가하면 반영 가능.

| 서번트 | 클래스 | ★ | DB 인물 | person_id | imp |
|--------|--------|---|---------|-----------|-----|
| Van Gogh | foreigner | 5 | Vincent van Gogh | 8117638 | 98 |
| Martha | rider | 4 | Martha Graham | 11382444 | 95 |
| Georgios | rider | 2 | Georgios Papanikolaou | 4884238 | 92 |
| Iyo | ruler | 4 | Taira no Kiyomori | 1634407 | 90 |
| Sieg | caster | 4 | Jerry Siegel | 8132250 | 88 |
| Amor | ruler | 5 | Mamoru Oshii | 9751659 | 85 |
| Vlad III | lancer | 4 | Vlad III Dracula | 14610760 | 70 |
| Jaguar Warrior | lancer | 3 | Jaguar Warrior | 14610688 | 70 |
| Nemo | rider | 5 | Taira no Munemori | 3321338 | 68 |
| Diarmuid Ua Duibhne | saber | 4 | Diarmuid Ua Duibhne | 14610657 | 65 |
| Sétanta | saber | 4 | Sétanta (Cú Chulainn) | 14610655 | 65 |
| Euryale | archer | 3 | Euryale | 14610666 | 65 |
| Aśvatthāman | archer | 4 | Aśvatthāman | 14610635 | 65 |
| Osakabehime | archer | 4 | Osakabehime | 14610720 | 65 |
| Cú Chulainn | lancer | 3 | Sétanta (Cú Chulainn) | 14610655 | 65 |
| Fionn mac Cumhaill | lancer | 4 | Fionn mac Cumhaill | 14610668 | 65 |
| Brynhild | lancer | 5 | Brynhildr | 14610647 | 65 |
| Caenis | lancer | 4 | Caeneus (born Caenis) | 14610648 | 65 |
| Bhīma | lancer | 5 | Bhīma | 14610643 | 65 |
| Europa | rider | 5 | Europa | 14610665 | 65 |
| Asclepius | caster | 3 | Asclepius | 14610633 | 65 |
| Daikokuten | caster | 4 | Daikokuten | 14610656 | 65 |
| Hildr | assassin | 4 | Hildr | 14610679 | 65 |
| Tezcatlipoca | assassin | 5 | Tezcatlipoca | 14610751 | 65 |
| Sitonai | alterEgo | 5 | Sitonai | 14610743 | 65 |
| Taisui Xingjun | alterEgo | 4 | Taisui Xingjun | 14610748 | 65 |
| Wandjina | foreigner | 5 | Wandjina | 14610763 | 65 |
| Tlāloc | pretender | 4 | Tlāloc | 14610755 | 65 |
| Yamato Takeru | saber | 5 | Yamato Takeru no Mikoto | 14610765 | 60 |
| Robin Hood | archer | 3 | Robin Hood | 14610731 | 60 |
| Dobrynya Nikitich | rider | 4 | Dobrynya Nikitich | 14610658 | 60 |
| Kashin Koji | assassin | 5 | Kashin Koji | 14610692 | 60 |
| Kijyo Koyo | berserker | 4 | Kijyo Koyo | 14610695 | 60 |
| Mélusine | ruler | 5 | Mélusine | 14610708 | 60 |
| Medb | saber | 4 | Mohamed Medbouh | 8211310 | 30 |
| Nitocris | caster | 4 | Nitocris | 12997624 | 12 |
| William Tell | archer | 3 | William Tell | 6663324 | 5 |
| Chacha | berserker | 4 | Vladimir Chachanidze | 11277655 | 5 |

---

## 2. DB 미등재 — 신화/전설 (분류 완료)

### 2-1. 신화 인물 (40명)

| 서번트 (EN) | 서번트 (JP) | 서번트 (KO) | 클래스 | ★ |
|------------|-----------|-----------|--------|---|
| Sigurd | シグルド | 시구르드 | saber | 5 |
| Beni-Enma | 紅閻魔 | 베니엔마 | saber | 5 |
| Medusa | メドゥーサ | 메두사 | saber | 5 |
| Gilgamesh | ギルガメッシュ | 길가메시 | archer | 5 |
| Orion | オリオン | 오리온 | archer | 5 |
| Arjuna | アルジュナ | 아르주나 | archer | 5 |
| Ishtar | イシュタル | 이슈타르 | archer | 5 |
| Enkidu | エルキドゥ | 엘키두 | lancer | 5 |
| Scáthach | スカサハ | 스카사하 | lancer | 5 |
| Tamamo-no-Mae (Lancer) | 玉藻の前 | 타마모노마에 | lancer | 5 |
| Ereshkigal | エレシュキガル | 에레쉬키갈 | lancer | 5 |
| Queen Medb | 女王メイヴ | 여왕 메이브 | rider | 5 |
| Quetzalcoatl | ケツァル・コアトル | 케찰코아틀 | rider | 5 |
| Achilles | アキレウス | 아킬레우스 | rider | 5 |
| Odysseus | オデュッセウス | 오디세우스 | rider | 5 |
| Galatea | ガラテア | 갈라테아 | berserker | 5 |
| Kukulcan | ククルカン | 쿠쿨칸 | foreigner | 5 |
| Rama | ラーマ | 라마 | saber | 4 |
| Karna (Santa) | カルナ〔サンタ〕 | 카르나[산타] | saber | 4 |
| Atalante | アタランテ | 아탈란테 | archer | 4 |
| Chiron | ケイローン | 케이론 | archer | 4 |
| Nezha | 哪吒 | 나타 | lancer | 4 |
| Valkyrie | ワルキューレ | 발키리 | lancer | 4 |
| Ibaraki-Douji (Lancer) | 茨木童子 | 이바라키도지 | lancer | 4 |
| Circe | キルケー | 키르케 | caster | 4 |
| Shuten-Douji (Caster) | 酒呑童子 | 슈텐도지 | caster | 4 |
| Stheno | ステンノ | 스테노 | assassin | 4 |
| Heracles | ヘラクレス | 헤라클레스 | berserker | 4 |
| Penthesilea | ペンテシレイア | 펜테실레이아 | berserker | 4 |
| Duryodhana | ドゥリーヨダナ | 두료다나 | berserker | 4 |
| Gorgon | ゴルゴーン | 고르곤 | avenger | 4 |
| Fergus mac Róich | フェルグス・マック・ロイ | 퍼거스 막 로이 | saber | 3 |
| Thēseus | テセウス | 테세우스 | saber | 3 |
| Romulus | ロムルス | 로물루스 | lancer | 3 |
| Hektor | ヘクトール | 헥토르 | lancer | 3 |
| Medea | メディア | 메데이아 | caster | 3 |
| Paris | パリス | 파리스 | archer | 2 |
| Jason | イアソン | 이아손 | saber | 1 |
| Asterios | アステリオス | 아스테리오스 | berserker | 1 |
| Aŋra Mainiiu | アンリマユ | 앙리 마유 | avenger | 0 |

### 2-2. 전설 인물 (35명)

| 서번트 (EN) | 서번트 (JP) | 서번트 (KO) | 클래스 | ★ |
|------------|-----------|-----------|--------|---|
| Altria Pendragon | アルトリア・ペンドラゴン | 알트리아 펜드래곤 | saber | 5 |
| Mordred | モードレッド | 모드레드 | saber | 5 |
| Arthur Pendragon (Prototype) | アーサー・ペンドラゴン〔プロトタイプ〕 | 아서 펜드래곤(프로토타입) | saber | 5 |
| Astolfo (Saber) | アストルフォ | 아스톨포 | saber | 5 |
| Bradamante | ブラダマンテ | 브라다만테 | lancer | 5 |
| Britomart | ブリトマート | 브리토마트 | lancer | 5 |
| Merlin | マーリン | 멀린 | caster | 5 |
| Scheherazade | シェヘラザード | 셰에라자드 | caster | 5 |
| Semiramis | セミラミス | 세미라미스 | assassin | 5 |
| Huyan Zhuo | 呼延灼 | 호연작 | assassin | 5 |
| Morgan | モルガン | 모르간 | berserker | 5 |
| Pope Johanna | 女教皇ヨハンナ | 여교황 요한나 | ruler | 5 |
| Oberon | オベロン | 오베론 | pretender | 5 |
| Lady Avalon | レディ・アヴァロン | 레이디 아발론 | pretender | 5 |
| Gawain | ガウェイン | 가웨인 | saber | 4 |
| Siegfried | ジークフリート | 지크프리트 | saber | 4 |
| Lancelot | ランスロット | 랜슬롯 | saber | 4 |
| Roland | ローラン | 롤랑 | saber | 4 |
| Watanabe-no-Tsuna | 渡辺綱 | 와타나베노 츠나 | saber | 4 |
| Gareth (Saber) | ガレス | 가레스 | saber | 4 |
| Tristan | トリスタン | 트리스탄 | archer | 4 |
| Kiyohime (Lancer) | 清姫 | 키요히메 | lancer | 4 |
| Percival | パーシヴァル | 퍼시벌 | lancer | 4 |
| Sakata Kintoki (Rider) | 坂田金時 | 사카타 킨토키 | rider | 4 |
| Habetrot | ハベトロット | 하베트롯 | rider | 4 |
| Huang Feihu | 黄飛虎 | 황비호 | rider | 4 |
| Queen of Sheba | シバの女王 | 시바의 여왕 | caster | 4 |
| Kiichi Hogen | 鬼一法眼 | 키이치 호겐 | assassin | 4 |
| Beowulf | ベオウルフ | 베오울프 | berserker | 4 |
| Kriemhild | クリームヒルト | 크림힐트 | berserker | 4 |
| Bedivere | ベディヴィエール | 베디비어 | saber | 3 |
| Red Hare | 赤兎馬 | 적토마 | rider | 3 |
| Mandricardo | マンドリカルド | 만드리카르도 | rider | 3 |
| Musashibou Benkei | 武蔵坊弁慶 | 무사시보 벤케이 | lancer | 2 |
| Paul Bunyan | ポール・バニヤン | 폴 버니언 | berserker | 1 |

### 2-3. 역사 인물 (DB 미등재, 14명)

실존 인물이지만 persons 테이블에 없음. 추가 필요 여부 판단.

| 서번트 (EN) | 서번트 (JP) | 서번트 (KO) | 클래스 | ★ |
|------------|-----------|-----------|--------|---|
| Miyamoto Musashi | 宮本武蔵 | 미야모토 무사시 | saber | 5 |
| Okita Souji | 沖田総司 | 오키타 소지 | saber | 5 |
| Ivan the Terrible | イヴァン雷帝 | 이반 뇌제 | rider | 5 |
| Kōnstantînos XI | コンスタンティノス11世 | 콘스탄티누스 11세 | rider | 5 |
| Anastasia | アナスタシア | 아나스타샤 | caster | 5 |
| Amakusa Shirou | 天草四郎 | 아마쿠사 시로 | ruler | 5 |
| Taira-no-Kagekiyo | 平景清 | 타이라노 카게키요 | avenger | 5 |
| Abigail Williams | アビゲイル・ウィリアムズ | 애비게일 윌리엄스 | foreigner | 5 |
| Chevalier d'Eon | シュヴァリエ・デオン | 슈발리에 데옹 | saber | 4 |
| Qin Liangyu | 秦良玉 | 진양옥 | lancer | 4 |
| Houzouin Inshun | 宝蔵院胤舜 | 호조인 인슈운 | lancer | 3 |
| Geronimo | ジェロニモ | 제로니모 | caster | 3 |
| Fuuma "Evil-wind" Kotarou | 風魔小太郎 | 후마 코타로 | assassin | 3 |
| Okada Izo | 岡田以蔵 | 오카다 이조 | assassin | 3 |

### 2-4. 가공 인물 (8명)

| 서번트 (EN) | 서번트 (JP) | 서번트 (KO) | 클래스 | ★ | 출처 |
|------------|-----------|-----------|--------|---|------|
| Sherlock Holmes | シャーロック・ホームズ | 셜록 홈즈 | ruler | 5 | |
| Edmond Dantès | 巌窟王 | 암굴왕 | avenger | 5 | |
| Voyager | ボイジャー | 보이저 | foreigner | 5 | |
| Frankenstein (Saber) | フランケンシュタイン | 프랑켄슈타인 | saber | 4 | |
| Don Quixote | ドン・キホーテ | 돈키호테 | lancer | 4 | |
| Mephistopheles | メフィストフェレス | 메피스토펠레스 | caster | 3 | |
| Henry Jekyll & Hyde | ヘンリー・ジキル＆ハイド | 헨리 지킬&하이드 | assassin | 3 | |
| Phantom of the Opera | ファントム・オブ・ジ・オペラ | 팬텀 오브 디 오페라 | assassin | 2 | |

---

## 3. 미분류 — DB 매치 없음 (112명)

아직 분류 안 된 서번트. 신화/전설/역사/FGO오리지널 구분 필요.
일부는 Section 2 인물의 변형 (Alter, Summer 등).

| 서번트 (EN) | 서번트 (JP) | 서번트 (KO) | 클래스 | ★ |
|------------|-----------|-----------|--------|---|
| Altera | アルテラ | 알테라 | saber | 5 |
| Dioscuri | ディオスクロイ | 디오스쿠로이 | saber | 5 |
| Ibuki-Douji | 伊吹童子 | 이부키도지 | saber | 5 |
| Senji Muramasa | 千子村正 | 센지 무라마사 | saber | 5 |
| Okita Souji Alter | 沖田総司〔オルタ〕 | 오키타 소지(얼터) | saber | 5 |
| Hai Bà Trưng | 徴姉妹 | 쯩 자매 | saber | 5 |
| リチャードⅠ世 | リチャードⅠ世 | 리처드 1세 | saber | 5 |
| パッションリップ | パッションリップ |  | saber | 5 |
| 近藤勇 | 近藤勇 |  | saber | 5 |
| ロード・ログレス | ロード・ログレス |  | saber | 5 |
| Super Orion | 超人オリオン | 초인 오리온 | archer | 5 |
| Durgā | ドゥルガー | 두르가 | archer | 5 |
| ツタンカーメン | ツタンカーメン |  | archer | 5 |
| ラーヴァ／ティアマト | ラーヴァ／ティアマト |  | archer | 5 |
| Romulus=Quirinus | ロムルス＝クィリヌス | 로물루스=퀴리누스 | lancer | 5 |
| Vritra | ヴリトラ | 브리트라 | lancer | 5 |
| Tam Lin Lancelot | 妖精騎士ランスロット | 요정기사 랜슬롯 | lancer | 5 |
| ビショーネ | ビショーネ |  | lancer | 5 |
| インドラ | インドラ |  | lancer | 5 |
| エリザベート・バートリー | エリザベート・バートリー |  | lancer | 5 |
| Altria Pendragon Alter | アルトリア・ペンドラゴン〔オルタ〕 | 알트리아 펜드래곤(얼터) | rider | 5 |
| アンドロメダ | アンドロメダ | 안드로메다 | rider | 5 |
| ネモ／ノア | ネモ／ノア |  | rider | 5 |
| Scáthach-Skadi | スカサハ＝スカディ | 스카사하=스카디 | caster | 5 |
| Altria Caster | アルトリア・キャスター | 알트리아 캐스터 | caster | 5 |
| Aesc the Rain Witch | 雨の魔女トネリコ | 비의 마녀 토네리코 | caster | 5 |
| 久遠寺有珠 | 久遠寺有珠 | 쿠온지 아리스 | caster | 5 |
| 小野小町 | 小野小町 |  | caster | 5 |
| Mysterious Heroine X | 謎のヒロインX | 수수께끼의 히로인 X | assassin | 5 |
| "First Hassan" | “山の翁” | “산의 노인” | assassin | 5 |
| Koyanskaya of Light | 光のコヤンスカヤ | 빛의 코얀스카야 | assassin | 5 |
| 河上彦斎 | 河上彦斎 |  | assassin | 5 |
| ロウヒ | ロウヒ |  | berserker | 5 |
| リリス | リリス |  | berserker | 5 |
| メタトロン・ジャンヌ | メタトロン・ジャンヌ |  | ruler | 5 |
| Kingprotea | キングプロテア | 킹프로테아 | alterEgo | 5 |
| Ashiya Douman | 蘆屋道満 | 아시야 도만 | alterEgo | 5 |
| Manannan mac Lir | マナナン・マク・リール〔バゼット〕 | 마나난 막 리르[바제트] | alterEgo | 5 |
| Super Bunyan | スーパーバニヤン | 슈퍼 버니언 | alterEgo | 5 |
| Larva/Tiamat | ラーヴァ／ティアマト | 라바/티아마트 | alterEgo | 5 |
| ひびき＆千鍵 | ひびき＆千鍵 |  | alterEgo | 5 |
| カズラドロップ | カズラドロップ |  | alterEgo | 5 |
| Space Ishtar | スペース・イシュタル | 스페이스 이슈타르 | avenger | 5 |
| 巌窟王　モンテ・クリスト | 巌窟王　モンテ・クリスト | 암굴왕 몽테크리스토 | avenger | 5 |
| 源頼光／丑御前 | 源頼光／丑御前 | 미나모토노 라이코/우시고젠 | avenger | 5 |
| Great Stone Statue God | 大いなる石像神 | 위대한 석상신 | moonCancer | 5 |
| Archetype: EARTH | アーキタイプ：アース | 아키타입 : 어스 | moonCancer | 5 |
| ＢＢドバイ | ＢＢドバイ |  | moonCancer | 5 |
| 謎の代行者C.I.E.L | 謎の代行者C.I.E.L |  | moonCancer | 5 |
| 玉兎 | 玉兎 |  | moonCancer | 5 |
| Koyanskaya of Dark | 闇のコヤンスカヤ | 어둠의 코얀스카야 | foreigner | 5 |
| 蒼崎青子 | 蒼崎青子 | 아오자키 아오코 | foreigner | 5 |
| ファンタズムーン | ファンタズムーン |  | pretender | 5 |
| ダンテ・アリギエーリ | ダンテ・アリギエーリ |  | pretender | 5 |
| テュフォン・エフェメロス | テュフォン・エフェメロス |  | pretender | 5 |
| Sodom's Beast/Draco | ソドムズビースト／ドラコー | 소돔즈 비스트/드라코 | beast | 5 |
| エレシュキガル | エレシュキガル |  | beastEresh | 5 |
| Ｕ－オルガマリー | Ｕ－オルガマリー |  | unBeastOlgaMarie | 5 |
| Lakshmi Bai | ラクシュミー・バーイー | 락슈미 바이 | saber | 4 |
| Tam Lin Gawain | 妖精騎士ガウェイン | 요정기사 가웨인 | saber | 4 |
| 宮本伊織 | 宮本伊織 | 미야모토 이오리 | saber | 4 |
| 黒姫 | 黒姫 |  | saber | 4 |
| Attila the San | アルテラ・ザ・サン〔タ〕 | 알테라 더 산[타] | archer | 4 |
| Anne Bonny & Mary Read | アン・ボニー＆メアリー・リード | 앤 보니&메리 리드 | archer | 4 |
| Tam Lin Tristan | 妖精騎士トリスタン | 요정기사 트리스탄 | archer | 4 |
| Anastasia & Viy | アナスタシア＆ヴィイ | 아나스타샤&비이 | archer | 4 |
| UDK-Barghest | ＵＤＫ－バーゲスト | UDK-바게스트 | archer | 4 |
| Jeanne d'Arc Alter Santa Lily | ジャンヌ・ダルク・オルタ・サンタ・リリィ | 잔 다르크 얼터 산타 릴리 | lancer | 4 |
| Minamoto-no-Raikou | 源頼光 | 미나모토노 라이코 | lancer | 4 |
| Pārvatī | パールヴァティー | 파르바티 | lancer | 4 |
| Nagao Kagetora | 長尾景虎 | 나가오 카게토라 | lancer | 4 |
| Mysterious Alter Ego Λ | 謎のアルターエゴ・Λ | 수수께끼의 얼터에고・Λ | lancer | 4 |
| Utsumi Erice | 宇津見エリセ | 우츠미 에리세 | lancer | 4 |
| Yu Mei-ren | 虞美人 | 우미인 | lancer | 4 |
| ドブルイニャ・ニキチッチ | ドブルイニャ・ニキチッチ |  | lancer | 4 |
| ヴァン・ゴッホ〔マイナー〕 | ヴァン・ゴッホ〔マイナー〕 |  | lancer | 4 |
| アショカ王 | アショカ王 |  | lancer | 4 |
| 美遊・エーデルフェルト | 美遊・エーデルフェルト |  | lancer | 4 |
| 原田左之助 | 原田左之助 |  | lancer | 4 |
| クリームヒルト | クリームヒルト |  | rider | 4 |
| Irisviel | アイリスフィール〔天の衣〕 | 아이리스필(하늘의 옷) | caster | 4 |
| 由井正雪 | 由井正雪 | 유이 쇼세츠 | caster | 4 |
| Katou "Black Kite" Danzo | 加藤段蔵 | 카토 단조 | assassin | 4 |
| Okita J. Souji | オキタ・Ｊ・ソウジ | 오키타・J・소지 | assassin | 4 |
| Ortlinde | オルトリンデ | 오르트린데 | assassin | 4 |
| Thrúd | スルーズ | 스루드 | assassin | 4 |
| 耀星のハサン | 耀星のハサン | 요성의 하산 | assassin | 4 |
| 静希草十郎 | 静希草十郎 | 시즈키 소쥬로 | berserker | 4 |
| 呼延灼 | 呼延灼 |  | berserker | 4 |
| Astraea | アストライア | 아스트라이아 | ruler | 4 |
| Mecha Eli-chan | メカエリチャン | 메카에리짱 | alterEgo | 4 |
| Mecha Eli-chan Mk.II | メカエリチャンⅡ号機 | 메카에리짱 Ⅱ호기 | alterEgo | 4 |
| ジュネス・クレーン | ジュネス・クレーン |  | alterEgo | 4 |
| Mysterious Ranmaru X | 謎の蘭丸X | 수수께끼의 란마루 X | avenger | 4 |
| 徐福 | 徐福 |  | avenger | 4 |
| 藤堂平助 | 藤堂平助 |  | avenger | 4 |
| 終わりのエリザベート | 終わりのエリザベート |  | avenger | 4 |
| 岸波白野 | 岸波白野 |  | moonCancer | 4 |
| テノチティトラン | テノチティトラン |  | moonCancer | 4 |
| Mysterious Heroine XX | 謎のヒロインXX | 수수께끼의 히로인 XX | foreigner | 4 |
| Mysterious Idol X | 謎のアイドルX〔オルタ〕 | 수수께끼의 아이돌 X(얼터) | foreigner | 4 |
| Cnoc na Riabh Yaraändoo | ノクナレア・ヤラアーンドゥ | 노크나레아・야라안두 | foreigner | 4 |
| 謎のヒロインXX〔オルタ〕 | 謎のヒロインXX〔オルタ〕 |  | foreigner | 4 |
| Elisa the Nine-Tattooed Dragon | 九紋竜エリザ | 구문룡 엘리자 | pretender | 4 |
| Cait Cú MikoCer | ケット・クー・ミコケル | 캐트 쿠 미코케르 | pretender | 4 |
| アレッサンドロ・ディ・カリオストロ | アレッサンドロ・ディ・カリオストロ | 알레산드로 디 칼리오스트로 | pretender | 4 |
| アビゲイル・ウィリアムズ〔サンタ〕 | アビゲイル・ウィリアムズ〔サンタ〕 |  | pretender | 4 |
| Sugitani Zenjubou | 杉谷善住坊 | 스기타니 젠쥬보 | archer | 3 |
| Hassan of the Hundred Personas | 百貌のハサン | 백모의 하산 | assassin | 3 |
| Hassan of the Serenity | 静謐のハサン | 정밀의 하산 | assassin | 3 |
| Hassan of the Cursed Arm | 呪腕のハサン | 주완의 하산 | assassin | 2 |
| Sasaki Kojirou | 佐々木小次郎 | 사사키 코지로 | assassin | 1 |
