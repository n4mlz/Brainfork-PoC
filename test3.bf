; デッドロックを意図的に発生させ得るコード（説明用）

[-]        ; cell0 = 0
>[-]       ; cell1 = 0
>[-]       ; cell2 = 0 (出力用)
< <        ; dp=cell0

{  ; 2スレッド
  (          ; lock cell0
    > (      ; lock cell1
      <<     ; dp=cell0
      +      ; cell0++
      >>     ; dp=cell2
      ; PRINT 'A' (Left thread passed critical section)
      +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++.
      [-]
      < <    ; dp=cell0
    )        ; unlock cell1
  )          ; unlock cell0
| 
  > (        ; lock cell1
    ~ ~      ; 0.2s 待つ（タイミング調整）
    < (      ; lock cell0  ← 逆順
      >>     ; dp=cell2
      ; PRINT 'B' (Right thread passed critical section)
      ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++.
      [-]
      < <    ; dp=cell0
    )        ; unlock cell0
  )          ; unlock cell1
}
