# run-001 後の限定変更

- V small候補は従来の個別upper/M<1e-10のみ。upperの小さい順に、累積upper/M≤1e-8の範囲だけsmallとし、残りをactiveへ戻す。log領域・finite・丸め超過fail-closed。分割はactive最大risk。全cell massは常に積分へ含める。
- 最終polar GL32全cell massを分母に再分類・active risk/gateを再評価し、分母と規則名を保存する。閾値は変更しない。
- cellのGL8/16を最終同一partitionで再利用。Vの固定Legendre nodes/weightsをcache。W/A/S/Jの積分コードはbyte同一。
- Cartesianは24/48を必ず保存。未達時だけ64、さらに96へ進み、最新2段差≤2e-7かつ最新対polar GL32差≤5e-7を要求。128は追加しない。実node構造から残評価予算を事前判定。2 million/4096 cell上限は維持。
- BudgetExceededへ既存の最終完全partition診断、処理stage、既に終わった照合値、残予算/必要点数を添付。例外後の追加評価なし。途中splitでは両子cellが終わるまで親を保持。mesh全nodeの再開機能は追加しない。
- run-001回収adapterと旧gateの型/finite/診断検証。非V390+V2成功を旧値・旧来歴で保持し、失敗・未試行だけ新規計算。担当pair_id範囲を明示し、outside_shardを停止と区別。mergeは文章契約のみ。

観測された失敗の主因をsmall制約と断定しない。親からの診断では92予算例外のうち89件がalternate GL24、3件がCartesian。4未収束joint/VはCartesian24/48差が約1.18–1.31e-6で基準未達、omittedは既に合格。polar/48の近さは真誤差の証明ではない。今回の変更で速度・完走・収束が改善する保証はない。

元run・旧失敗を新gateで遡及的に成功へ変更しない。PML/PR67/入力/prior/支持/全精度閾値は不変。科学run/import/tests/Git登録は行わない。
