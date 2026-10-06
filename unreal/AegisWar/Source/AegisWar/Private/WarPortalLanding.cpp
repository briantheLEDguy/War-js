#include "WarPortalLanding.h"
#include "WarCharacter.h"
#include "WarZoneAnchor.h"
#include "WarZonePortal.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"

namespace WarPortalLanding
{
    bool Find(AWarCharacter* Character,const FVector& Arrival,const AWarZoneAnchor* Zone,
        float SearchRadius,const AActor* Source,const AActor* Destination,FVector& Landing,FString& Error)
    {
        auto* World=Character ? Character->GetWorld() : nullptr;
        const auto* Capsule=Character ? Character->GetCapsuleComponent() : nullptr;
        const auto* Movement=Character ? Character->GetCharacterMovement() : nullptr;
        if (!World || !Capsule || !Movement || !Zone || Zone->GetWorld()!=World || Arrival.ContainsNaN()
            || !FMath::IsFinite(SearchRadius) || SearchRadius<0 || SearchRadius>600
            || AWarZoneAnchor::FindAt(World,Arrival)!=Zone)
        { Error=TEXT("Destination has no unambiguous validated arrival area.");return false; }
        const float Radius=Capsule->GetScaledCapsuleRadius(),Half=Capsule->GetScaledCapsuleHalfHeight();
        if (!FMath::IsFinite(Radius) || !FMath::IsFinite(Half) || Radius<=0 || Half<Radius)
        { Error=TEXT("Destination character clearance is unavailable.");return false; }
        FCollisionQueryParams GroundQuery(SCENE_QUERY_STAT(PortalGround),false,Character);
        if (Source) GroundQuery.AddIgnoredActor(Source);
        if (Destination) GroundQuery.AddIgnoredActor(Destination);
        const auto Floor=[&](const FVector& Seed,float Range,FHitResult& Hit) {
            // An object query excludes standing characters. A channel query can
            // hit their capsules and incorrectly stack later arrivals on them.
            return World->LineTraceSingleByObjectType(Hit,Seed+FVector(0,0,Range),Seed-FVector(0,0,Range),
                FCollisionObjectQueryParams(ECC_WorldStatic),GroundQuery) && Hit.GetComponent()
                && Hit.GetComponent()->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block && Hit.ImpactNormal.Z>=.7
                && AWarZoneAnchor::FindAt(World,Hit.ImpactPoint)==Zone;
        };
        FHitResult Reference;
        if (!Floor(Arrival,5000,Reference))
        { Error=TEXT("Destination has no safe landing surface.");return false; }
        const auto Center=[&](const FHitResult& Hit) {
            return Hit.ImpactPoint+FVector(0,0,AWarZonePortal::CapsuleGroundOffset(Half,Radius,Hit.ImpactNormal.Z));
        };
        FCollisionQueryParams CorridorQuery=GroundQuery;
        // Occupants reserve the final landing. Static geometry and support still
        // constrain the complete corridor within the destination's arrival pad.
        for (TActorIterator<APawn> It(World);It;++It) CorridorQuery.AddIgnoredActor(*It);
        const auto Connected=[&](const FHitResult& Target) {
            const int32 Steps=FMath::Max(1,FMath::CeilToInt(FVector::Dist2D(Reference.ImpactPoint,Target.ImpactPoint)/40.));
            FVector PreviousCenter=Center(Reference);double PreviousZ=Reference.ImpactPoint.Z;
            for (int32 Step=0;Step<=Steps;++Step)
            {
                FHitResult Support;
                const FVector Seed=FMath::Lerp(Reference.ImpactPoint,Target.ImpactPoint,double(Step)/Steps);
                if (!Floor(Seed,Movement->MaxStepHeight+5,Support)
                    || FMath::Abs(Support.ImpactPoint.Z-Seed.Z)>Movement->MaxStepHeight
                    || FMath::Abs(Support.ImpactPoint.Z-PreviousZ)>Movement->MaxStepHeight) return false;
                const FVector NextCenter=Center(Support);
                if (World->OverlapBlockingTestByProfile(NextCenter,FQuat::Identity,TEXT("Pawn"),
                    FCollisionShape::MakeCapsule(Radius,Half),CorridorQuery)) return false;
                FHitResult Wall;
                if (World->SweepSingleByProfile(Wall,PreviousCenter,NextCenter,FQuat::Identity,TEXT("Pawn"),
                    FCollisionShape::MakeCapsule(Radius,Half),CorridorQuery)) return false;
                PreviousCenter=NextCenter;PreviousZ=Support.ImpactPoint.Z;
            }
            return true;
        };
        for (float Ring:{0.f,150.f,300.f,450.f,600.f})
        {
            if (Ring>SearchRadius) continue;
            for (int32 Index=0;Index<(Ring==0 ? 1 : 12);++Index)
            {
                const double Angle=Index*PI/6;
                const FVector Seed=Reference.ImpactPoint+FVector(FMath::Cos(Angle),FMath::Sin(Angle),0)*Ring;
                FHitResult Ground;
                if (!Floor(Seed,Movement->MaxStepHeight+5,Ground)
                    || FMath::Abs(Ground.ImpactPoint.Z-Reference.ImpactPoint.Z)>Movement->MaxStepHeight) continue;
                const FVector Candidate=Center(Ground);
                if (World->OverlapBlockingTestByProfile(Candidate,FQuat::Identity,TEXT("Pawn"),
                    FCollisionShape::MakeCapsule(Radius,Half),GroundQuery) || !Connected(Ground)) continue;
                Landing=Candidate;return true;
            }
        }
        Error=TEXT("Destination landing is obstructed. You remain protected until space is ready.");return false;
    }
}
