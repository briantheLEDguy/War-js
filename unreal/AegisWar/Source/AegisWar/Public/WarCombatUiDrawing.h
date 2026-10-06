#pragma once
#include "CoreMinimal.h"
#include "WarCombatUiSettings.h"
#include "WarCombatFeedback.h"
#include "WarFloatingCombatText.h"

class AHUD;
class UCanvas;
enum class EWarUiDraw : uint8 { Box, Line, Text };
struct FWarUiDraw
{
    EWarUiDraw Kind = EWarUiDraw::Box;
    int32 Element = INDEX_NONE;
    FVector2D A, B;
    FLinearColor Color;
    FString Text;
    float Weight = 1;
};
struct FWarCombatUiDrawList
{
    TArray<FWarUiDraw> Items;
    TMap<int32,FBox2D> Handles;
};
namespace WarCombatUi
{
    AEGISWAR_API void Reticle(FWarCombatUiDrawList& D,const FWarCombatUiSettings& S,bool Enemy,FBox2D Body,float Scale);
    AEGISWAR_API void HealthBar(FWarCombatUiDrawList& D,const FWarCombatUiSettings& S,bool Enemy,FVector2D Head,float Health,float Scale);
    AEGISWAR_API void Number(FWarCombatUiDrawList& D,const FWarCombatUiSettings& S,const FWarFloatingCombatNumber& N,FVector2D Head,float Scale);
    AEGISWAR_API void Panel(FWarCombatUiDrawList& D,const FWarCombatUiSettings& S,bool Enemy,FVector2D View,float Scale,const FString& Name,float Health,float Max,const FString& Cast,float CastProgress);
    AEGISWAR_API void Notices(FWarCombatUiDrawList& D,const FWarCombatUiSettings& S,FVector2D View,float Scale,const TArray<FWarCombatNotice>& Notices,double Now);
    AEGISWAR_API void Canvas(AHUD* Hud,UCanvas* Canvas,const FWarCombatUiDrawList& D);
    AEGISWAR_API int32 HitTest(const FWarCombatUiDrawList& D,FVector2D Point);
    AEGISWAR_API FBox2D ElementBounds(int32 Id,const FWarCombatUiSettings& S,FVector2D View,float Scale);
}

/** Pure presentation timeline; never calls combat, actors, audio or networking. */
struct AEGISWAR_API FWarCombatUiPreview
{
    double Time = 0;
    int32 Mode = 1, NextProc = 0;
    bool Paused = false;
    TArray<FWarFloatingCombatNumber> Numbers;
    void Replay(int32 NewMode);
    void Advance(float Delta,const FWarCombatUiSettings& Settings);
    FWarCombatUiDrawList Draw(const FWarCombatUiSettings& Settings,FVector2D View,int32 Selected) const;
};
