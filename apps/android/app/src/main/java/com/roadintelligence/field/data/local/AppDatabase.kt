package com.roadintelligence.field.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.roadintelligence.field.data.local.dao.InspectionDao
import com.roadintelligence.field.data.local.dao.InspectionMediaDao
import com.roadintelligence.field.data.local.dao.RoadDao
import com.roadintelligence.field.data.local.dao.SyncQueueDao
import com.roadintelligence.field.data.local.entity.InspectionEntity
import com.roadintelligence.field.data.local.entity.InspectionMediaEntity
import com.roadintelligence.field.data.local.entity.RoadEntity
import com.roadintelligence.field.data.local.entity.RoadSegmentEntity
import com.roadintelligence.field.data.local.entity.SyncQueueEntity

@Database(
    entities = [
        InspectionEntity::class,
        InspectionMediaEntity::class,
        RoadEntity::class,
        RoadSegmentEntity::class,
        SyncQueueEntity::class
    ],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun inspectionDao(): InspectionDao
    abstract fun inspectionMediaDao(): InspectionMediaDao
    abstract fun roadDao(): RoadDao
    abstract fun syncQueueDao(): SyncQueueDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "road_intelligence_field.db"
                )
                .fallbackToDestructiveMigration()
                .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
