#include "WarCapitalProofSubsystem.h"
#include "WarCharacter.h"
#include "WarPlayerController.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "Algo/Reverse.h"

void UWarCapitalProofSubsystem::StartCastleTraversal()
{
    auto* Player=Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Character=Player ? Cast<AWarCharacter>(Player->GetPawn()) : nullptr;
    if (!Character) { Finish(false,TEXT("Castle walking character missing.")); return; }
    if (CastleRoutes.IsEmpty())
    {
        FString Json; TSharedPtr<FJsonObject> Root;
        const TSharedPtr<FJsonObject>* Routes=nullptr;
        if (!FFileHelper::LoadFileToString(Json,*FPaths::Combine(FPaths::ProjectContentDir(),TEXT("Migration/capital-development.json")))
            || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root) || !Root.IsValid()
            || !Root->TryGetObjectField(TEXT("castleRoutes"),Routes))
        { Finish(false,TEXT("Castle route fixture is missing.")); return; }
        for (const FString Name : { FString(TEXT("keep")),FString(TEXT("battlement")),
            FString(TEXT("floor1")),FString(TEXT("floor2")),FString(TEXT("floor3")),FString(TEXT("floor4")) })
        {
            const TArray<TSharedPtr<FJsonValue>>* Points=nullptr;
            if (!(*Routes)->TryGetArrayField(Name,Points) || Points->Num()<3 || Points->Num()>100)
            { Finish(false,TEXT("Invalid castle route.")); return; }
            TArray<FVector> Route;
            for (const auto& Value : *Points)
            {
                const TArray<TSharedPtr<FJsonValue>>* XYZ=nullptr;
                if (!Value->TryGetArray(XYZ) || XYZ->Num()!=3) { Finish(false,TEXT("Invalid castle waypoint.")); return; }
                FVector Point;
                for (int32 Axis=0; Axis<3; ++Axis)
                    if (!(*XYZ)[Axis]->TryGetNumber(Point[Axis])) { Finish(false,TEXT("Non-numeric castle waypoint.")); return; }
                if (Point.ContainsNaN() || Point.GetAbsMax()>100000) { Finish(false,TEXT("Invalid castle route bounds.")); return; }
                Route.Add(Point);
            }
            CastleRoutes.Add(Route);
            Algo::Reverse(Route); CastleRoutes.Add(MoveTemp(Route));
        }
    }
    const FVector Start=CastleRoutes[CastleRouteIndex][0]+FVector(0,0,Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+5);
    if (!Character->TeleportTo(Start,FRotator::ZeroRotator,false,false))
    { Finish(false,TEXT("Castle route start is blocked.")); return; }
    Character->GetCharacterMovement()->StopMovementImmediately();
    Character->GetCharacterMovement()->MaxWalkSpeed=300;
    Character->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
    Player->SetControlRotation(FRotator::ZeroRotator);
    CityRouteIndex=1; CityWalkStartedAt=GetWorld()->GetTimeSeconds(); CastleAirborneAt=-1; Stage=11;
}

void UWarCapitalProofSubsystem::TickCastleTraversal()
{
    auto* Player=Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Character=Player ? Cast<AWarCharacter>(Player->GetPawn()) : nullptr;
    if (!Character || Character->IsDevelopmentFlying()
        || Character->GetCapsuleComponent()->GetCollisionEnabled()==ECollisionEnabled::NoCollision)
    { Finish(false,TEXT("Castle traversal lost its colliding walking character.")); return; }
    const double Now=GetWorld()->GetTimeSeconds();
    if (Now-CityWalkStartedAt>45)
    { Finish(false,FString::Printf(TEXT("Castle route %d stalled at waypoint %d: %s"),CastleRouteIndex,CityRouteIndex,*Character->GetActorLocation().ToString())); return; }
    if (!Character->GetCharacterMovement()->IsMovingOnGround())
    {
        if (CastleAirborneAt<0) CastleAirborneAt=Now;
        if (Now-CastleAirborneAt>1) { Finish(false,TEXT("Castle staircase lost walkable support.")); return; }
    }
    else CastleAirborneAt=-1;
    const auto& Route=CastleRoutes[CastleRouteIndex];
    while (CityRouteIndex<Route.Num()-1 && FVector::Dist2D(Character->GetActorLocation(),Route[CityRouteIndex])<40)
        ++CityRouteIndex;
    FVector Feet=Character->GetActorLocation(); Feet.Z-=Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if (CityRouteIndex==Route.Num()-1 && FVector::Dist2D(Feet,Route.Last())<35
        && FMath::Abs(Feet.Z-Route.Last().Z)<25 && Character->GetCharacterMovement()->IsMovingOnGround())
    {
        Character->GetCharacterMovement()->StopMovementImmediately(); ++CastleRouteIndex;
        if (CastleRouteIndex<CastleRoutes.Num()) { StartCastleTraversal(); return; }
        bCastleTraversalVerified=true;
        if (FParse::Param(FCommandLine::Get(),TEXT("WarProofScreenshot")))
        {
            // Photograph a previously walked endpoint; this never substitutes for traversal.
            const FVector Roof=CastleRoutes[0].Last()+FVector(0,0,Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+5);
            if (!Character->TeleportTo(Roof,FRotator(0,180,0),false,false))
            { Finish(false,TEXT("Verified roof viewpoint became blocked.")); return; }
            Player->GetLocalCameraState().Yaw=180;
            Player->GetLocalCameraState().Pitch=-25;
            Player->GetLocalCameraState().Distance=900;
        }
        Finish(true,TEXT("Character walked through the castle entrances and up/down the keep roof, four upper floors and battlement.")); return;
    }
    FVector Direction=Route[CityRouteIndex]-Feet; Direction.Z=0;
    Character->AddMovementInput(Direction.GetSafeNormal(),1.f);
}
