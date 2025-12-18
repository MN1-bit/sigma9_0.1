# Research: Aesthetic Background Particle Effects for Sigma9

> **작성일**: 2025-12-18
> **목적**: Sigma9 트레이딩 시스템의 평시(Idle/Default) 상태에서 사용자에게 심미적 만족감을 주고, 고급스러운 분위기를 연출할 수 있는 배경 파티클 이펙트 연구.

---

## 1. Design Philosophy: "Alive but Unobtrusive"

트레이딩 시스템의 배경은 **정보 가독성**을 해치지 않으면서도 시스템이 **"살아있음(Alive)"**을 은유적으로 표현해야 합니다. 너무 화려하거나 빠른 움직임은 시선을 분산시키므로, 느리고 부드러운(Fluid) 움직임이 핵심입니다.

## 2. Recommended Effects (Top 5)

다음은 현대적인 UI/UX 트렌드와 Fintech 분야 중 럭셔리 세그먼트에서 선호되는 파티클 스타일입니다.

### 2.1 The Constellation (Network)
- **설명**: 점(Node)들이 느리게 부유하며, 서로 가까워질 때 선(Line)으로 연결되는 효과.
- **상징성**: **연결성, 데이터, 신경망, 글로벌 마켓**.
- **심미성**: 기하학적이며 이지적인 느낌. 선이 생겼다 사라지는 모습이 유기적인 호흡처럼 느껴짐.
- **적합성**: ⭐️⭐️⭐️⭐️⭐️ (Quant/AI 트레이딩과 가장 잘 어울림)
- **Variation**: 마우스 커서 주변으로만 연결되게 하여 인터랙티브한 재미 요소 추가 가능.

### 2.2 Digital Dust (Gold/Silver Fireflies)
- **설명**: 극도로 미세한 입자들이 공기 중의 먼지나 반딧불이처럼 아주 천천히 부유하며 반짝이는 효과.
- **상징성**: **희망, 잠재력, 고요함**.
- **심미성**: 몽환적이고 감성적인 분위기. 배경이 어두울수록 금색/은색 입자가 돋보여 고급스러움(Premium Feel) 극대화.
- **적합성**: ⭐️⭐️⭐️⭐️ (장시간 보고 있어도 눈이 편안함)

### 2.3 Bokeh Flow (Soft Orbs)
- **설명**: 초점이 나간 듯한 부드러운 원형 빛 뭉치들이 배경에서 천천히 흐르는 효과.
- **상징성**: **유동성(Liquidity), 흐름**.
- **심미성**: 아크릴(Acrylic) 효과와 결합 시 뎁스(Depth)감이 극대화됨.
- **적합성**: ⭐️⭐️⭐️ (차트가 많은 화면에서는 다소 산만할 수 있음, 로그인 화면이나 대기 화면에 적합)

### 2.4 Mathematical Flow (Vector Field)
- **설명**: 보이지 않는 그리드 위를 흐르는 벡터 장(Field)을 따라 입자들이 물결치듯 이동하는 효과 (Perlin Noise 활용).
- **상징성**: **시장 흐름, 파동, 수학적 질서**.
- **심미성**: 자연의 바람이나 물결 같으면서도 수학적인 질서가 느껴짐.
- **적합성**: ⭐️⭐️⭐️⭐️ (세련되고 전문적인 느낌)

### 2.5 Matrix Rain (Modern Minimalist Ver.)
- **설명**: 고전적인 매트릭스 레인이 아닌, 매우 얇고 투명한 숫자나 기호들이 비처럼 내리는 것이 아니라, 공기 중에 떠다니는(Levitating) 형태.
- **상징성**: **순수 데이터, 알고리즘**.
- **심미성**: 글자가 흐릿하게 나타났다 사라지는(Fade in/out) 연출로 신비로움 강조.
- **적합성**: ⭐️⭐️⭐️ (호불호가 갈릴 수 있음)

---

## 3. Technical Implementation Suggestion (PyQt6)

Sigma9의 현재 아키텍처(PyQt6 + Acrylic)에서 구현 효율성과 심미성을 고려한 추천 조합입니다.

| 요소 | 추천 설정 | 이유 |
|------|-----------|------|
| **Core Effect** | **Constellation + Digital Dust** | 데이터의 연결성(AI)과 고급스러움(Premium)을 동시에 잡는 하이브리드 접근. |
| **Color Palette** | **Gold (#FFD700) & Slate Blue (#6A5ACD)** | 신뢰(Blue)와 부(Gold)를 상징. 투명도(Alpha)를 0.1~0.3으로 낮게 설정하여 은은하게. |
| **Interaction** | **Mouse Repel/Attract** | 마우스 움직임에 살짝 반응하여 사용자와의 교감 유도. |
| **Performance** | **QPainter vs OpenGL** | `QPainter`로도 충분하나, 파티클 수가 200개 이상이면 OpenGL 위젯 고려. 현재는 가벼운 `QPainter` 권장. |

## 4. Conclusion

**"Constellation (별자리/네트워크)" 스타일을 기본으로 하되, "Digital Dust"를 배경에 깔아 깊이감을 주는 것**을 제안합니다. 이는 Sigma9이 추구하는 **"인공지능 기반의 정밀한 트레이딩"**이라는 브랜드 이미지와 완벽하게 부합합니다.
