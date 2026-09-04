package com.puretext.launcher.util

import android.content.Context
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.util.Log

/**
 * Flashlight toggle via the dedicated torch API (CameraManager.setTorchMode),
 * added specifically so apps don't need full camera/CAMERA permission just to
 * blink the flash. Every OEM camera quirk is swallowed -- a torch command
 * that silently does nothing is fine, one that crashes the launcher is not.
 */
object Torch {
    @Volatile
    private var isOn = false

    fun toggle(context: Context, forceOn: Boolean? = null) {
        try {
            val manager = context.getSystemService(Context.CAMERA_SERVICE) as? CameraManager ?: return
            val cameraId = manager.cameraIdList.firstOrNull { id ->
                manager.getCameraCharacteristics(id).get(CameraCharacteristics.FLASH_INFO_AVAILABLE) == true
            } ?: return
            val target = forceOn ?: !isOn
            manager.setTorchMode(cameraId, target)
            isOn = target
        } catch (e: Exception) {
            Log.w("Torch", "Could not toggle flashlight", e)
        }
    }
}
