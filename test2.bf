; 2 つのセルを順にロックして操作（逆順で解放）

[-]        ; cell0 = 0
>[-]       ; cell1 = 0
>[-]       ; cell2 = 0 (dummy)
< <        ; dp = cell0

{
  (              ; Thread-A: lock cell0
    ~~~          ; ★ 0.3s 待っている間に Thread-B が cell1 を掴む
    > (          ; lock cell1  ← ここで循環待ちが完成しデッドロック
  )              ; （到達しない）
|
  > (            ; Thread-B: lock cell1
    ~~~          ; ★ 同様に待つ
    < (          ; lock cell0  ← デッドロック成立
  )              ; （到達しない）
}
