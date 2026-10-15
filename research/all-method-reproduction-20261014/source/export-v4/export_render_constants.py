"""review済みrendererの表示専用定数。測定moduleへのimportを分離。"""
CREDITS_NAME = 'audio_credits.html'
PUBLIC_IDS = ('librispeech_1089-134686-0008', 'librispeech_1188-133604-0003')
PUBLIC_METHODS = ('original', 'hnm', 'world_harvest', 'facodec', 'hifiglot', 'llsm2', 'magphase')
FAMILIES = {
    1: 'UTMOSv2予測MOS', 2: 'SCOREQ参照あり距離', 3: 'ViSQOL Audio独立48kHz群',
    4: '増分CER/WER', 5: 'ECAPA話者類似度', 6: '局所聴覚帯域距離',
    7: '音高操作追従', 8: '音量操作追従', 9: '局所時間・全長', 10: '音色・傾斜',
    11: '操作干渉', 12: '編集量と予測品質の曲線', 13: '既存人間評定と近傍一致',
    14: '音素ABX', 15: '線形読み出し', 16: '補間', 17: '表現量子化への頑健性',
    18: '品質と表現量',
}
