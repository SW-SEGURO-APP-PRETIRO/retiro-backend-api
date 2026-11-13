-- Prueba de la bitácora inmutable. Todo ocurre dentro de una transacción que se deshace:
-- no queda ningún dato de prueba en la tabla.
BEGIN TRAN;
INSERT INTO auditoria_eventoauditoria
    (institucion_id, secuencia, tipo, resultado, detalle, fecha, hash_anterior, hash_propio)
VALUES
    (99999, 1, 'PRUEBA', 'EXITO', '{}', SYSUTCDATETIME(), REPLICATE('0', 64), REPLICATE('p', 64));
GO
UPDATE auditoria_eventoauditoria SET tipo = 'HACK' WHERE institucion_id = 99999;
GO
DELETE FROM auditoria_eventoauditoria WHERE institucion_id = 99999;
GO
ROLLBACK TRAN;
GO
SELECT COUNT(*) AS filas_de_prueba_que_quedan FROM auditoria_eventoauditoria WHERE institucion_id = 99999;
GO