#include "WarDutchBastionProof.h"
#include "WarCitadelCookedContacts.h"
#include "WarCitadelProofJson.h"
#include "WarCitadelCapsulePolicy.h"
#include "WarCharacter.h"
#include "WarSiegeBattlefield.h"
#include "WarSiegeNavigation.h"
#include "WarCityDefinition.h"
#include "Blueprint/UserWidget.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "GameFramework/HUD.h"
#include "EngineUtils.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "PhysicsEngine/BodySetup.h"
#include "PhysicsEngine/BodyInstance.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/StaticMesh.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMemory.h"
#include "UnrealClient.h"
#include "RHIStats.h"
#include "ContentStreaming.h"
#include "HAL/IConsoleManager.h"

namespace
{
    FVector Point(const TArray<TSharedPtr<FJsonValue>>& Values)
    {
        return Values.Num()==3 ? FVector(Values[0]->AsNumber(),Values[1]->AsNumber(),Values[2]->AsNumber()) : FVector::ZeroVector;
    }
    struct FWidthPawnRestore
    {
        AWarCharacter* Pawn;
        UCharacterMovementComponent* Movement;
        FTransform Transform;
        FFindFloorResult Floor;
        FVector Velocity;
        EMovementMode Mode;
        uint8 Custom;
        bool Teleported, ForceFloor;
        TWeakObjectPtr<UPrimitiveComponent> Base;
        FName BaseBone;
        explicit FWidthPawnRestore(AWarCharacter* InPawn) : Pawn(InPawn),Movement(InPawn->GetCharacterMovement()),
            Transform(InPawn->GetActorTransform()),Floor(Movement->CurrentFloor),Velocity(Movement->Velocity),
            Mode(Movement->MovementMode),Custom(Movement->CustomMovementMode),
            Teleported(Movement->bJustTeleported),ForceFloor(Movement->bForceNextFloorCheck),
            Base(InPawn->GetMovementBase()),BaseBone(InPawn->GetBasedMovement().BoneName) {}
        ~FWidthPawnRestore()
        {
            Pawn->SetActorTransform(Transform,false,nullptr,ETeleportType::TeleportPhysics);
            Movement->SetMovementMode(Mode,Custom); Movement->CurrentFloor=Floor; Movement->Velocity=Velocity;
            Pawn->SetBase(Base.Get(),BaseBone);
            Movement->bJustTeleported=Teleported; Movement->bForceNextFloorCheck=ForceFloor;
        }
    };
    FString CapsuleObstruction(AWarCharacter* Pawn,const FVector& Center)
    {
        const auto* Capsule=Pawn->GetCapsuleComponent();
        FCollisionQueryParams Query(SCENE_QUERY_STAT(CitadelWidthPlacement),false,Pawn);
        TArray<FOverlapResult> Hits;
        Pawn->GetWorld()->OverlapMultiByChannel(Hits,Center,Capsule->GetComponentQuat(),Capsule->GetCollisionObjectType(),
            FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight()),Query,
            FCollisionResponseParams(Capsule->GetCollisionResponseToChannels()));
        for (const auto& Hit:Hits) if (Hit.bBlockingHit)
            return Hit.GetActor() ? Hit.GetActor()->GetPathName() : TEXT("unnamed blocking component");
        return FString();
    }
    FString RoutePlacementObstruction(AWarCharacter* Pawn,const FVector& Center,
        WarCitadelRouteWidth::FOverlapEvidence& Evidence,const TCHAR* Role)
    {
        const auto* Capsule=Pawn->GetCapsuleComponent();
        const FQuat Rotation=Capsule->GetComponentQuat();
        const double Radius=Capsule->GetScaledCapsuleRadius(),Half=Capsule->GetScaledCapsuleHalfHeight();
        const auto* Proof=Pawn->GetWorld()->GetSubsystem<UWarDutchBastionProof>();
        if (!IsInGameThread() || !WarCitadelCapsulePolicy::Matches(Pawn)
            || (Proof && !Proof->MatchesCapturedKinematics(Pawn))
            || Center.ContainsNaN() || Rotation.ContainsNaN() || !Rotation.IsNormalized()
            || !FMath::IsFinite(Radius) || !FMath::IsFinite(Half) || Radius<=0 || Half<Radius)
        { ++Evidence.Queries;++Evidence.Unresolved;Evidence.LastDisposition=TEXT("unresolved");return TEXT("invalid route capsule query"); }
        FCollisionQueryParams Query(SCENE_QUERY_STAT(CitadelWidthPlacement),false,Pawn);
        TArray<FOverlapResult> Hits;
        // Query and read-locked geometry inspection run synchronously on the game
        // thread. Never feed this wrapper cached hits or saved diagnostic JSON.
        Pawn->GetWorld()->OverlapMultiByChannel(Hits,Center,Rotation,Capsule->GetCollisionObjectType(),
            FCollisionShape::MakeCapsule(Radius,Half),Query,FCollisionResponseParams(Capsule->GetCollisionResponseToChannels()));
        if (!Hits.ContainsByPredicate([](const FOverlapResult& Hit){return Hit.bBlockingHit;}))
        { ++Evidence.Queries;++Evidence.RawClear;Evidence.LastDisposition=TEXT("raw_clear");return FString(); }
        const auto Resolution=WarCitadelCookedContacts::ResolveOverlaps(Hits,Center,Rotation,Radius,Half,Query.bTraceComplex);
        ++Evidence.Queries;Evidence.RawBlockingHits+=Resolution.RawBlockingHits;
        using Decision=WarCitadelCookedContacts::EContactDecision;
        const bool Accounting=Resolution.UniqueBodies==Resolution.SeparatedBodies+Resolution.BlockedBodies+Resolution.UnresolvedBodies;
        const bool Clear=Accounting && (Resolution.Decision==Decision::RawClear || Resolution.Decision==Decision::Separated);
        if (Clear && Resolution.Decision==Decision::RawClear) { ++Evidence.RawClear;Evidence.LastDisposition=TEXT("raw_clear"); }
        else if (Clear) { ++Evidence.Separated;Evidence.LastDisposition=TEXT("all_raw_contacts_proven_separated"); }
        else if (Resolution.Decision==Decision::Blocked) { ++Evidence.Blocked;Evidence.LastDisposition=TEXT("blocked"); }
        else { ++Evidence.Unresolved;Evidence.LastDisposition=TEXT("unresolved"); }
        if (Resolution.RawBlockingHits>0)
        {
            auto Record=MakeShared<FJsonObject>(),Pose=MakeShared<FJsonObject>();
            Pose->SetArrayField(TEXT("center"),{MakeShared<FJsonValueNumber>(Center.X),MakeShared<FJsonValueNumber>(Center.Y),MakeShared<FJsonValueNumber>(Center.Z)});
            Pose->SetArrayField(TEXT("quaternion"),{MakeShared<FJsonValueNumber>(Rotation.X),MakeShared<FJsonValueNumber>(Rotation.Y),MakeShared<FJsonValueNumber>(Rotation.Z),MakeShared<FJsonValueNumber>(Rotation.W)});
            Pose->SetNumberField(TEXT("radiusCm"),Radius);Pose->SetNumberField(TEXT("halfHeightCm"),Half);Pose->SetStringField(TEXT("role"),Role);
            Record->SetObjectField(TEXT("query"),Pose);
            Record->SetObjectField(TEXT("resolution"),!Clear && FString(Role)==TEXT("seed_probe")
                ? WarCitadelProofJson::RejectedSeedSummary(Resolution.Diagnostic.ToSharedRef()) : Resolution.Diagnostic.ToSharedRef());
            Evidence.Contacts.Add(MakeShared<FJsonValueObject>(Record));
        }
        if (Clear) return FString();
        for (const auto& Hit:Hits) if (Hit.bBlockingHit)
            return Hit.GetActor() ? Hit.GetActor()->GetPathName() : TEXT("unresolved blocking component");
        return TEXT("unresolved route capsule query");
    }
    TArray<TSharedPtr<FJsonValue>> WidthVector(const FVector& Value)
    {
        return {MakeShared<FJsonValueNumber>(Value.X),MakeShared<FJsonValueNumber>(Value.Y),MakeShared<FJsonValueNumber>(Value.Z)};
    }
    TSharedPtr<FJsonObject> WidthHit(const FHitResult& Hit)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetBoolField(TEXT("blocking"),Hit.bBlockingHit);
        Row->SetBoolField(TEXT("startPenetrating"),Hit.bStartPenetrating);
        Row->SetNumberField(TEXT("penetrationDepthCm"),Hit.PenetrationDepth);Row->SetNumberField(TEXT("time"),Hit.Time);
        Row->SetArrayField(TEXT("impact"),WidthVector(Hit.ImpactPoint));Row->SetArrayField(TEXT("location"),WidthVector(Hit.Location));
        Row->SetArrayField(TEXT("normal"),WidthVector(Hit.Normal));Row->SetArrayField(TEXT("impactNormal"),WidthVector(Hit.ImpactNormal));
        Row->SetArrayField(TEXT("traceStart"),WidthVector(Hit.TraceStart));Row->SetArrayField(TEXT("traceEnd"),WidthVector(Hit.TraceEnd));
        Row->SetStringField(TEXT("actor"),Hit.GetActor() ? Hit.GetActor()->GetPathName() : TEXT(""));
        Row->SetStringField(TEXT("component"),Hit.GetComponent() ? Hit.GetComponent()->GetPathName() : TEXT(""));
        Row->SetNumberField(TEXT("item"),Hit.Item);Row->SetNumberField(TEXT("myItem"),Hit.MyItem);
        Row->SetNumberField(TEXT("faceIndex"),Hit.FaceIndex);Row->SetStringField(TEXT("bone"),Hit.BoneName.ToString());return Row;
    }
    TSharedPtr<FJsonObject> WidthFloor(const FFindFloorResult& Floor)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetBoolField(TEXT("walkable"),Floor.IsWalkableFloor());
        Row->SetBoolField(TEXT("lineTrace"),Floor.bLineTrace);Row->SetNumberField(TEXT("sweepDistanceCm"),Floor.FloorDist);
        Row->SetNumberField(TEXT("lineDistanceCm"),Floor.LineDist);Row->SetNumberField(TEXT("distanceCm"),Floor.GetDistanceToFloor());
        Row->SetObjectField(TEXT("hit"),WidthHit(Floor.HitResult));return Row;
    }
    FVector WidthRampDelta(const UCharacterMovementComponent* Movement,const FVector& Delta,const FHitResult& Hit,bool LineTrace)
    {
        // ComputeGroundMovementDelta is protected. Preserve its native branch and
        // speed policy for this world-Z corridor; the full capsule sweep is real.
        const FVector Normal=Hit.ImpactNormal;
        if (!LineTrace && Normal.Z<1-KINDA_SMALL_NUMBER && Normal.Z>KINDA_SMALL_NUMBER
            && Hit.Normal.Z>KINDA_SMALL_NUMBER && Movement->IsWalkable(Hit))
        {
            const float Dot=FVector::DotProduct(Normal,Delta);
            const FVector Ramp(Delta.X,Delta.Y,-Dot/Normal.Z);
            return Movement->bMaintainHorizontalGroundVelocity ? Ramp : Ramp.GetSafeNormal()*Delta.Size();
        }
        return Delta;
    }
}

TSharedPtr<FJsonObject> WarCitadelRouteWidth::CapsuleContactDiagnostic(AWarCharacter* Pawn,const FVector& Center)
{
    if (!Pawn || !Pawn->GetWorld() || !Pawn->GetCapsuleComponent() || !Pawn->GetCharacterMovement()
        || Center.ContainsNaN()) return nullptr;
    const auto* Capsule=Pawn->GetCapsuleComponent();auto* World=Pawn->GetWorld();
    const FQuat Rotation=Capsule->GetComponentQuat();const auto Channel=Capsule->GetCollisionObjectType();
    const auto Shape=FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight());
    auto Result=MakeShared<FJsonObject>();Result->SetBoolField(TEXT("diagnosticOnly"),true);
    Result->SetStringField(TEXT("world"),World->GetPathName());Result->SetNumberField(TEXT("worldType"),int32(World->WorldType));
    Result->SetArrayField(TEXT("center"),WidthVector(Center));
    Result->SetArrayField(TEXT("quaternion"),{MakeShared<FJsonValueNumber>(Rotation.X),MakeShared<FJsonValueNumber>(Rotation.Y),
        MakeShared<FJsonValueNumber>(Rotation.Z),MakeShared<FJsonValueNumber>(Rotation.W)});
    Result->SetNumberField(TEXT("radiusCm"),Shape.GetCapsuleRadius());Result->SetNumberField(TEXT("halfHeightCm"),Shape.GetCapsuleHalfHeight());
    Result->SetNumberField(TEXT("channel"),int32(Channel));
    const auto ComponentEvidence=[](UPrimitiveComponent* Component)
    {
        auto Row=MakeShared<FJsonObject>();if (!Component) return Row;
        Row->SetStringField(TEXT("path"),Component->GetPathName());Row->SetNumberField(TEXT("uniqueId"),Component->GetUniqueID());
        Row->SetNumberField(TEXT("mobility"),int32(Component->Mobility));
        Row->SetNumberField(TEXT("collisionEnabled"),int32(Component->GetCollisionEnabled()));
        Row->SetNumberField(TEXT("objectType"),int32(Component->GetCollisionObjectType()));
        Row->SetNumberField(TEXT("pawnResponse"),int32(Component->GetCollisionResponseToChannel(ECC_Pawn)));
        Row->SetBoolField(TEXT("physicsStateCreated"),Component->IsPhysicsStateCreated());
        Row->SetArrayField(TEXT("boundsOrigin"),WidthVector(Component->Bounds.Origin));
        Row->SetArrayField(TEXT("boundsExtent"),WidthVector(Component->Bounds.BoxExtent));
        Row->SetStringField(TEXT("transform"),Component->GetComponentTransform().ToString());
        if (const auto* Static=Cast<UStaticMeshComponent>(Component))
            Row->SetStringField(TEXT("mesh"),Static->GetStaticMesh() ? Static->GetStaticMesh()->GetPathName() : TEXT(""));
        if (const auto* Setup=Component->GetBodySetup())
        {
            auto Body=MakeShared<FJsonObject>();Body->SetStringField(TEXT("path"),Setup->GetPathName());
            Body->SetStringField(TEXT("guid"),Setup->BodySetupGuid.ToString());
            Body->SetNumberField(TEXT("collisionTraceFlag"),int32(Setup->CollisionTraceFlag));
            Body->SetNumberField(TEXT("resolvedCollisionTraceFlag"),int32(Setup->GetCollisionTraceFlag()));
            Body->SetBoolField(TEXT("doubleSidedGeometry"),Setup->bDoubleSidedGeometry);
            Body->SetBoolField(TEXT("createdPhysicsMeshes"),Setup->bCreatedPhysicsMeshes);
            Body->SetBoolField(TEXT("failedPhysicsMeshes"),Setup->bFailedToCreatePhysicsMeshes);
            Body->SetBoolField(TEXT("hasCookedCollisionData"),Setup->bHasCookedCollisionData);
            Body->SetNumberField(TEXT("liveTriangleMeshCount"),Setup->TriMeshGeometries.Num());
            Body->SetNumberField(TEXT("simpleElementCount"),Setup->AggGeom.GetElementCount());Row->SetObjectField(TEXT("bodySetup"),Body);
        }
        return Row;
    };
    Result->SetObjectField(TEXT("capsule"),ComponentEvidence(Pawn->GetCapsuleComponent()));
    const auto QueryEvidence=[&](const FCollisionQueryParams& Query,const FCollisionResponseParams& Responses)
    {
        auto Row=MakeShared<FJsonObject>();
        Row->SetBoolField(TEXT("traceComplex"),Query.bTraceComplex);Row->SetBoolField(TEXT("findInitialOverlaps"),Query.bFindInitialOverlaps);
        Row->SetBoolField(TEXT("returnFaceIndex"),Query.bReturnFaceIndex);Row->SetBoolField(TEXT("returnPhysicalMaterial"),Query.bReturnPhysicalMaterial);
        Row->SetBoolField(TEXT("ignoreBlocks"),Query.bIgnoreBlocks);Row->SetBoolField(TEXT("ignoreTouches"),Query.bIgnoreTouches);
        Row->SetBoolField(TEXT("skipNarrowPhase"),Query.bSkipNarrowPhase);
        Row->SetBoolField(TEXT("traceIntoSubComponents"),Query.bTraceIntoSubComponents);
        Row->SetBoolField(TEXT("replaceHitWithSubComponents"),Query.bReplaceHitWithSubComponents);
        Row->SetNumberField(TEXT("ignoreMask"),Query.IgnoreMask);Row->SetNumberField(TEXT("mobilityType"),int32(Query.MobilityType));
        TArray<TSharedPtr<FJsonValue>> Actors,Components,Channels;
        for (const auto Id:Query.GetIgnoredSourceObjects()) Actors.Add(MakeShared<FJsonValueNumber>(Id));
        for (const auto Id:Query.GetIgnoredComponents()) Components.Add(MakeShared<FJsonValueNumber>(Id));
        for (const uint8 Response:Responses.CollisionResponse.EnumArray) Channels.Add(MakeShared<FJsonValueNumber>(Response));
        Row->SetArrayField(TEXT("ignoredSourceIds"),Actors);Row->SetArrayField(TEXT("ignoredComponentIds"),Components);
        Row->SetArrayField(TEXT("responses"),Channels);
        TArray<FOverlapResult> Overlaps;const bool Blocking=World->OverlapMultiByChannel(Overlaps,Center,Rotation,Channel,Shape,Query,Responses);
        Row->SetBoolField(TEXT("overlapBlocking"),Blocking);TArray<TSharedPtr<FJsonValue>> Hits;
        for (const auto& Hit:Overlaps)
        {
            auto Item=MakeShared<FJsonObject>();Item->SetBoolField(TEXT("blocking"),Hit.bBlockingHit);
            Item->SetStringField(TEXT("actor"),Hit.GetActor() ? Hit.GetActor()->GetPathName() : TEXT(""));
            Item->SetNumberField(TEXT("item"),Hit.GetItemIndex());Item->SetNumberField(TEXT("myItem"),Hit.MyItemIndex);
            Item->SetBoolField(TEXT("physicsObjectPresent"),Hit.PhysicsObject!=nullptr);
            Item->SetStringField(TEXT("physicsObjectOwner"),Hit.PhysicsObjectOwner.IsValid() ? Hit.PhysicsObjectOwner->GetPathName() : TEXT(""));
            Item->SetObjectField(TEXT("component"),ComponentEvidence(Hit.GetComponent()));
            if (Hit.bBlockingHit && Hit.GetComponent())
                if (const auto* Body=Hit.GetComponent()->GetBodyInstance(NAME_None,true,Hit.GetItemIndex()))
                {
                    // Direct body queries bypass scene filtering. Compare only
                    // bodies already returned as blocking by the admission query.
                    auto Direct=MakeShared<FJsonObject>();Direct->SetBoolField(TEXT("bypassesSceneFiltering"),true);
                    Direct->SetStringField(TEXT("debugName"),Body->GetBodyDebugName());
                    Direct->SetNumberField(TEXT("instanceBodyIndex"),Body->InstanceBodyIndex);
                    Direct->SetNumberField(TEXT("overlapItemIndex"),Hit.GetItemIndex());
                    Direct->SetBoolField(TEXT("validBodyInstance"),Body->IsValidBodyInstance());
                    Direct->SetNumberField(TEXT("collisionEnabled"),int32(Body->GetCollisionEnabled()));
                    Direct->SetStringField(TEXT("worldTransform"),Body->GetUnrealWorldTransform().ToString());
                    Direct->SetBoolField(TEXT("traceComplex"),Query.bTraceComplex);
                    Direct->SetBoolField(TEXT("withoutMTD"),Body->OverlapTest(Center,Rotation,Shape,nullptr,Query.bTraceComplex));
                    FMTDResult MTD;MTD.Distance=0;MTD.Direction=FVector::ZeroVector;
                    Direct->SetBoolField(TEXT("withMTD"),Body->OverlapTest(Center,Rotation,Shape,&MTD,Query.bTraceComplex));
                    Direct->SetNumberField(TEXT("mtdDistanceCm"),MTD.Distance);Direct->SetArrayField(TEXT("mtdDirection"),WidthVector(MTD.Direction));
                    Direct->SetObjectField(TEXT("cookedTriangleWitness"),WarCitadelCookedContacts::Witness(Body,Center,Rotation,
                        Shape.GetCapsuleRadius(),Shape.GetCapsuleHalfHeight(),Query.bTraceComplex));
                    Item->SetObjectField(TEXT("directBodyQuery"),Direct);
                }
            Hits.Add(MakeShared<FJsonValueObject>(Item));
        }
        Row->SetArrayField(TEXT("overlaps"),Hits);TArray<TSharedPtr<FJsonValue>> Sweeps;
        // These matched sweeps cannot make a blocking overlap pass. Zero-length
        // and both directions disclose solver differences without moving the pawn.
        for (const double Z:{0.,.01,-.01})
        {
            auto Sweep=MakeShared<FJsonObject>();const FVector End=Center+FVector(0,0,Z);
            Sweep->SetArrayField(TEXT("start"),WidthVector(Center));Sweep->SetArrayField(TEXT("end"),WidthVector(End));
            FHitResult Single;Sweep->SetBoolField(TEXT("singleBlocking"),World->SweepSingleByChannel(Single,Center,End,Rotation,Channel,Shape,Query,Responses));
            Sweep->SetObjectField(TEXT("singleHit"),WidthHit(Single));TArray<FHitResult> Multi;
            Sweep->SetBoolField(TEXT("multiBlocking"),World->SweepMultiByChannel(Multi,Center,End,Rotation,Channel,Shape,Query,Responses));
            TArray<TSharedPtr<FJsonValue>> MultiRows;for (const auto& Hit:Multi) MultiRows.Add(MakeShared<FJsonValueObject>(WidthHit(Hit)));
            Sweep->SetArrayField(TEXT("multiHits"),MultiRows);Sweeps.Add(MakeShared<FJsonValueObject>(Sweep));
        }
        Row->SetArrayField(TEXT("matchedSweeps"),Sweeps);return Row;
    };
    FCollisionQueryParams Admission(SCENE_QUERY_STAT(CitadelWidthPlacement),false,Pawn);
    Result->SetObjectField(TEXT("admissionQuery"),QueryEvidence(Admission,FCollisionResponseParams(Capsule->GetCollisionResponseToChannels())));
    FCollisionQueryParams MovementQuery(SCENE_QUERY_STAT(CitadelWidthMovementComparison),false,Pawn);FCollisionResponseParams MovementResponses;
    Pawn->GetCharacterMovement()->InitCollisionParams(MovementQuery,MovementResponses);
    Result->SetObjectField(TEXT("movementQueryComparison"),QueryEvidence(MovementQuery,MovementResponses));
    TArray<TSharedPtr<FJsonValue>> IgnoreActors,IgnoreComponents;
    for (const auto* Actor:Capsule->GetMoveIgnoreActors()) if (Actor) IgnoreActors.Add(MakeShared<FJsonValueString>(Actor->GetPathName()));
    for (const auto* Component:Capsule->GetMoveIgnoreComponents()) if (Component) IgnoreComponents.Add(MakeShared<FJsonValueString>(Component->GetPathName()));
    Result->SetArrayField(TEXT("moveIgnoreActors"),IgnoreActors);Result->SetArrayField(TEXT("moveIgnoreComponents"),IgnoreComponents);
    return Result;
}

bool WarCitadelRouteWidth::SpawnPadSeed(const FVector& Anchor,double Width,double Radius,int32 Index,
    int32 X,int32 Y,const FVector2D& Gradient,FVector& Seed)
{
    if (Anchor.ContainsNaN() || !FMath::IsFinite(Width) || Width<600 || !FMath::IsFinite(Radius) || Radius<=0
        || Width<=Radius*2 || Index<0 || Index>5 || X<-2 || X>2 || Y<-2 || Y>2 || Gradient.ContainsNaN()
        || Gradient.Size()>1 || (Index>=2 && !Gradient.IsZero())) return false;
    const double Edge=Width/2-Radius,DX=X*Edge/2,DY=Y*Edge/2;
    Seed=Anchor+FVector(DX,DY,Gradient.X*DX+Gradient.Y*DY);return !Seed.ContainsNaN();
}

WarCitadelRouteWidth::FSupport WarCitadelRouteWidth::AdjustedSupport(AWarCharacter* Pawn,
    const FFindFloorResult& Before,const FVector& BeforeCenter,const FFindFloorResult& After,const FVector& AfterCenter)
{
    FSupport Result;Result.Distance=After.GetDistanceToFloor();Result.Impact=After.HitResult.ImpactPoint;
    if (!Pawn || !After.IsWalkableFloor() || After.HitResult.bStartPenetrating) return Result;
    if (!After.bLineTrace) { Result.Verified=true;return Result; }
    auto* Movement=Pawn->GetCharacterMovement();const auto* Capsule=Pawn->GetCapsuleComponent();
    if (!Movement || !Capsule) return Result;
    Result.Diagnostic=MakeShared<FJsonObject>();auto& Row=Result.Diagnostic;
    Row->SetObjectField(TEXT("beforeFloor"),WidthFloor(Before));Row->SetObjectField(TEXT("afterFloor"),WidthFloor(After));
    Row->SetArrayField(TEXT("beforeCenter"),WidthVector(BeforeCenter));Row->SetArrayField(TEXT("afterCenter"),WidthVector(AfterCenter));
    Row->SetBoolField(TEXT("verified"),false);
    if (!Before.bLineTrace || !Before.IsWalkableFloor() || Before.HitResult.bStartPenetrating
        || FVector::Dist2D(BeforeCenter,AfterCenter)>.0001 || !Before.HitResult.GetComponent()
        || Before.HitResult.GetComponent()!=After.HitResult.GetComponent()
        || Before.HitResult.GetComponent()->Mobility!=EComponentMobility::Static) return Result;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(CitadelIndependentLineSupport),false,Pawn);
    FCollisionResponseParams Responses;Movement->InitCollisionParams(Query,Responses);
    Query.bTraceIntoSubComponents=true;Query.bReplaceHitWithSubComponents=false;
    const double Half=Capsule->GetScaledCapsuleHalfHeight();FHitResult BeforeHit,AfterHit;
    const auto Trace=[&](const FVector& Center,FHitResult& Hit)
    {
        return Pawn->GetWorld()->LineTraceSingleByChannel(Hit,Center,Center-FVector(0,0,Half+MaxFloorDeviationCm),
            Capsule->GetCollisionObjectType(),Query,Responses) && Hit.IsValidBlockingHit()
            && !Hit.bStartPenetrating && Movement->IsWalkable(Hit)
            && Hit.GetActor()==After.HitResult.GetActor() && Hit.GetComponent()==After.HitResult.GetComponent();
    };
    const bool BeforeValid=Trace(BeforeCenter,BeforeHit),AfterValid=Trace(AfterCenter,AfterHit);
    const double BeforeDistance=BeforeCenter.Z-Half-BeforeHit.ImpactPoint.Z;
    const double ActualDistance=AfterCenter.Z-Half-AfterHit.ImpactPoint.Z;
    const double Corrected=Before.LineDist+AfterCenter.Z-BeforeCenter.Z;
    Row->SetObjectField(TEXT("beforeLine"),WidthHit(BeforeHit));Row->SetObjectField(TEXT("afterLine"),WidthHit(AfterHit));
    Row->SetNumberField(TEXT("beforeMeasuredDistanceCm"),BeforeDistance);
    Row->SetNumberField(TEXT("correctedBeforeDistanceCm"),Corrected);
    Row->SetNumberField(TEXT("afterMeasuredDistanceCm"),ActualDistance);
    Row->SetNumberField(TEXT("agreementEpsilonCm"),.1);
    Result.Verified=BeforeValid && AfterValid && FMath::Abs(BeforeDistance-Before.LineDist)<=.1
        && FMath::Abs(ActualDistance-Corrected)<=.1
        && ActualDistance>=UCharacterMovementComponent::MIN_FLOOR_DIST-.1
        && ActualDistance<=UCharacterMovementComponent::MAX_FLOOR_DIST+.1;
    Row->SetBoolField(TEXT("verified"),Result.Verified);
    if (Result.Verified) { Result.Distance=ActualDistance;Result.Impact=AfterHit.ImpactPoint; }
    return Result;
}

void WarCitadelRouteWidth::FOverlapEvidence::Append(const FOverlapEvidence& Other)
{
    Queries+=Other.Queries;RawClear+=Other.RawClear;Separated+=Other.Separated;
    Blocked+=Other.Blocked;Unresolved+=Other.Unresolved;RawBlockingHits+=Other.RawBlockingHits;
    Contacts.Append(Other.Contacts);if (Other.Queries>0) LastDisposition=Other.LastDisposition;
}

TSharedPtr<FJsonObject> WarCitadelRouteWidth::FOverlapEvidence::Json() const
{
    auto Result=MakeShared<FJsonObject>();Result->SetNumberField(TEXT("queries"),Queries);
    Result->SetNumberField(TEXT("rawClear"),RawClear);Result->SetNumberField(TEXT("separated"),Separated);
    Result->SetNumberField(TEXT("blocked"),Blocked);Result->SetNumberField(TEXT("unresolved"),Unresolved);
    Result->SetNumberField(TEXT("rawBlockingHits"),RawBlockingHits);Result->SetStringField(TEXT("lastDisposition"),LastDisposition);
    Result->SetArrayField(TEXT("contacts"),Contacts);return Result;
}

int32 WarCitadelRouteWidth::Intervals(const FVector& From,const FVector& To)
{
    const double Length=FVector::Dist2D(From,To);
    return From.ContainsNaN() || To.ContainsNaN() || !FMath::IsFinite(Length) || Length<.001 || Length>1000000
        ? 0 : FMath::Max(1,FMath::CeilToInt(Length/MaxSpacingCm));
}
bool WarCitadelRouteWidth::ReadSurface(const TSharedPtr<FJsonObject>& Object,const FString& RouteId,FSurface& Surface)
{
    Surface.KnotsCm.Empty();
    if (!Object || Object->Values.Num()!=7 || !Object->HasTypedField<EJson::Number>(TEXT("schemaVersion"))
        || !Object->HasTypedField<EJson::Array>(TEXT("knotsCm"))) return false;
    for (const TCHAR* Field:{TEXT("routeId"),TEXT("kind"),TEXT("meshId"),TEXT("boundaryPolicy"),TEXT("construction")})
        if (!Object->HasTypedField<EJson::String>(Field)) return false;
    FString Base=RouteId;if (!Base.RemoveFromEnd(TEXT(":forward"))) Base.RemoveFromEnd(TEXT(":reverse"));
    double Version=0;FString Id,Kind,Mesh,Boundary,Construction;const TArray<TSharedPtr<FJsonValue>>* Knots=nullptr;
    if (!Object->TryGetNumberField(TEXT("schemaVersion"),Version) || Version!=1
        || !Object->TryGetStringField(TEXT("routeId"),Id) || Id!=Base || Id.IsEmpty()
        || !Object->TryGetStringField(TEXT("kind"),Kind) || Kind!=TEXT("world_x_piecewise_linear")
        || !Object->TryGetStringField(TEXT("meshId"),Mesh) || Mesh!=TEXT("stairs_and_balconies")
        || !Object->TryGetStringField(TEXT("boundaryPolicy"),Boundary) || Boundary!=TEXT("closed_profile_domain_shared_boundaries_same_height")
        || !Object->TryGetStringField(TEXT("construction"),Construction) || Construction!=TEXT("continuous_paved_fan_ramp")
        || !Object->TryGetArrayField(TEXT("knotsCm"),Knots) || Knots->Num()<2 || Knots->Num()>64) return false;
    TArray<FVector2D> Parsed;
    for (const auto& Value:*Knots)
    {
        const TArray<TSharedPtr<FJsonValue>>* Pair=nullptr;double X=0,Z=0;
        if (!Value || Value->Type!=EJson::Array || !Value->TryGetArray(Pair) || Pair->Num()!=2
            || !(*Pair)[0] || !(*Pair)[1] || (*Pair)[0]->Type!=EJson::Number || (*Pair)[1]->Type!=EJson::Number
            || !(*Pair)[0]->TryGetNumber(X) || !(*Pair)[1]->TryGetNumber(Z)
            || !FMath::IsFinite(X) || !FMath::IsFinite(Z) || FMath::Abs(X)>1000000 || FMath::Abs(Z)>1000000) return false;
        if (Parsed.Num())
        {
            const FVector2D Previous=Parsed.Last();const double Run=X-Previous.X;
            if (Run<=0 || 1./FMath::Sqrt(1+FMath::Square((Z-Previous.Y)/Run))<.7) return false;
        }
        Parsed.Emplace(X,Z);
    }
    Surface.KnotsCm=MoveTemp(Parsed);return true;
}
bool WarCitadelRouteWidth::Height(const FSurface& Surface,double X,double& Z)
{
    const auto& Knots=Surface.KnotsCm;
    if (Knots.Num()<2 || !FMath::IsFinite(X) || X<Knots[0].X || X>Knots.Last().X) return false;
    for (int32 I=1;I<Knots.Num();++I) if (X<=Knots[I].X)
    {
        const double Run=Knots[I].X-Knots[I-1].X;
        if (Run<=0) return false;
        Z=FMath::Lerp(Knots[I-1].Y,Knots[I].Y,(X-Knots[I-1].X)/Run);return FMath::IsFinite(Z);
    }
    return false;
}
bool WarCitadelRouteWidth::Sample(const FVector& From,const FVector& To,double Width,double Radius,
    int32 Index,double Lane,FVector& Seed,double& Offset,const FSurface* Surface)
{
    const int32 Count=Intervals(From,To);
    if (!Count || Index<0 || Index>Count || !FMath::IsFinite(Width) || !FMath::IsFinite(Radius)
        || Radius<=0 || Width<=Radius*2 || (Lane!=-1 && Lane!=-.5 && Lane!=0 && Lane!=.5 && Lane!=1)) return false;
    const FVector Direction=(To-From).GetSafeNormal2D();
    Offset=Lane*(Width*.5-Radius);
    Seed=FMath::Lerp(From,To,double(Index)/Count)+FVector(-Direction.Y,Direction.X,0)*Offset;
    if (Surface && !Height(*Surface,Seed.X,Seed.Z)) return false;
    return !Seed.ContainsNaN();
}
WarCitadelRouteWidth::FPlacement WarCitadelRouteWidth::Ground(AWarCharacter* Pawn,const FVector& Feet)
{
    FPlacement Result;
    if (!Pawn || !Pawn->GetWorld() || Feet.ContainsNaN()) { Result.Reason=TEXT("invalid native pawn or seed");return Result; }
    const auto* Capsule=Pawn->GetCapsuleComponent(); auto* Movement=Pawn->GetCharacterMovement();
    if (!Capsule || !Movement || !WarCitadelCapsulePolicy::Matches(Pawn) || !Pawn->GetActorEnableCollision()
        || Capsule->GetCollisionEnabled()==ECollisionEnabled::NoCollision || Capsule->GetCollisionObjectType()!=ECC_Pawn)
    { Result.Reason=TEXT("native pawn capsule collision is unavailable");return Result; }
    if (Movement->MovementMode!=MOVE_Walking)
    { Result.Reason=TEXT("physical corridor probes require an already-walking proof pawn");return Result; }
    FWidthPawnRestore Restore(Pawn);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(CitadelWidthFloor),false,Pawn);
    FCollisionResponseParams Responses;Movement->InitCollisionParams(Query,Responses);
    Query.bTraceIntoSubComponents=true;Query.bReplaceHitWithSubComponents=false;FHitResult Line;
    if (!Pawn->GetWorld()->LineTraceSingleByChannel(Line,Feet+FVector(0,0,MaxFloorDeviationCm),
        Feet-FVector(0,0,MaxFloorDeviationCm),ECC_Pawn,Query,Responses))
    { Result.Reason=TEXT("floor missing within signed elevation tolerance");return Result; }
    Result.HitActor=Line.GetActor() ? Line.GetActor()->GetName() : TEXT("");
    if (!Movement->IsWalkable(Line)) { Result.Reason=TEXT("floor exceeds native walkable slope");return Result; }
    const double Half=Capsule->GetScaledCapsuleHalfHeight(),Radius=Capsule->GetScaledCapsuleRadius();
    const FVector Base(Feet.X,Feet.Y,Line.ImpactPoint.Z+Half+GroundClearanceCm);
    // A line at a stair tread can put the lower hemisphere into the next riser.
    // Find a clear lift within native step height, sweep the complete capsule down,
    // then let native floor finding/height adjustment establish the resting pose.
    const int32 Lifts=FMath::CeilToInt(Movement->MaxStepHeight/5.);
    for (int32 I=0;I<=Lifts;++I)
    {
        const FVector Above=Base+FVector(0,0,FMath::Min(double(Movement->MaxStepHeight),I*5.));
        const FString Obstruction=RoutePlacementObstruction(Pawn,Above,Result.Overlaps,TEXT("seed_probe"));
        if (!Obstruction.IsEmpty())
        {
            Result.HitActor=Obstruction;Result.Diagnostic=MakeShared<FJsonObject>();
            Result.Diagnostic->SetArrayField(TEXT("seed"),WidthVector(Feet));
            Result.Diagnostic->SetArrayField(TEXT("attemptedCenter"),WidthVector(Above));
            Result.Diagnostic->SetStringField(TEXT("obstructionActor"),Obstruction);
            Result.Diagnostic->SetObjectField(TEXT("capsuleContacts"),CapsuleContactDiagnostic(Pawn,Above));continue;
        }
        FHitResult Support;
        if (!Pawn->GetWorld()->SweepSingleByChannel(Support,Above,Base-FVector(0,0,Movement->MaxStepHeight+5),
            Capsule->GetComponentQuat(),ECC_Pawn,FCollisionShape::MakeCapsule(Radius,Half),Query,Responses)
            || Support.bStartPenetrating) continue;
        Pawn->SetActorLocation(Support.Location+FVector(0,0,GroundClearanceCm),false,nullptr,ETeleportType::TeleportPhysics);
        Movement->SetMovementMode(MOVE_Walking);
        Movement->FindFloor(Pawn->GetActorLocation(),Movement->CurrentFloor,false,&Support);
        if (!Movement->CurrentFloor.IsWalkableFloor()) continue;
        const FFindFloorResult Before=Movement->CurrentFloor;
        const FVector BeforeCenter=Pawn->GetActorLocation();
        Movement->AdjustFloorHeight();
        const FFindFloorResult Adjusted=Movement->CurrentFloor;
        const FFindFloorResult Floor=Movement->CurrentFloor;
        const auto SupportEvidence=AdjustedSupport(Pawn,Before,BeforeCenter,Floor,Pawn->GetActorLocation());
        Result.Center=Pawn->GetActorLocation(); Result.FloorImpact=SupportEvidence.Impact;
        Result.FloorNormalZ=Floor.HitResult.ImpactNormal.Z; Result.FloorDistance=SupportEvidence.Distance;
        Result.FloorActor=Floor.HitResult.GetActor() ? Floor.HitResult.GetActor()->GetName() : TEXT("");
        Result.Floor=SupportEvidence.Verified && Floor.IsWalkableFloor() && !Floor.HitResult.bStartPenetrating
            && FMath::Abs(Result.FloorImpact.Z-Feet.Z)<=MaxFloorDeviationCm
            && Result.FloorDistance>=UCharacterMovementComponent::MIN_FLOOR_DIST-.1
            && Result.FloorDistance<=UCharacterMovementComponent::MAX_FLOOR_DIST+.1;
        Result.HitActor=RoutePlacementObstruction(Pawn,Result.Center,Result.Overlaps,TEXT("floor_adjusted"));
        Result.Clear=Result.Floor && Result.HitActor.IsEmpty()
            && FVector::Dist2D(Result.Center,Feet)<=1;
        if (Result.Clear) { Result.Reason.Empty();Result.Diagnostic=SupportEvidence.Diagnostic;return Result; }
        Result.Diagnostic=MakeShared<FJsonObject>();Result.Diagnostic->SetArrayField(TEXT("seed"),WidthVector(Feet));
        Result.Diagnostic->SetArrayField(TEXT("center"),WidthVector(Result.Center));
        Result.Diagnostic->SetArrayField(TEXT("adjustment"),WidthVector(Result.Center-BeforeCenter));
        Result.Diagnostic->SetObjectField(TEXT("supportLine"),WidthHit(Line));
        Result.Diagnostic->SetObjectField(TEXT("supportSweep"),WidthHit(Support));
        Result.Diagnostic->SetObjectField(TEXT("beforeAdjustment"),WidthFloor(Before));
        Result.Diagnostic->SetObjectField(TEXT("afterAdjustment"),WidthFloor(Adjusted));
        FFindFloorResult Fresh;Movement->FindFloor(Pawn->GetActorLocation(),Fresh,false);
        Result.Diagnostic->SetObjectField(TEXT("freshFloor"),WidthFloor(Fresh));
        if (!Result.HitActor.IsEmpty()) Result.Diagnostic->SetObjectField(TEXT("capsuleContacts"),CapsuleContactDiagnostic(Pawn,Result.Center));
        if (SupportEvidence.Diagnostic) Result.Diagnostic->SetObjectField(TEXT("lineSupportVerification"),SupportEvidence.Diagnostic);
    }
    Result.Reason=Result.Floor ? TEXT("grounded full capsule placement or headroom is blocked")
        : TEXT("no grounded native capsule floor within slope, step and elevation limits");
    return Result;
}
WarCitadelRouteWidth::FTransition WarCitadelRouteWidth::Traverse(AWarCharacter* Pawn,const FVector& From,const FVector& To,const FSurface* Surface)
{
    FTransition Result;
    if (!Pawn || !Pawn->GetCharacterMovement()) { Result.Reason=TEXT("native movement unavailable");return Result; }
    if (!Pawn->GetCharacterMovement()->GetGravityDirection().Equals(FVector(0,0,-1),.0001))
    { Result.Reason=TEXT("signed world-Z corridors require the actual standard gravity direction");return Result; }
    if (Surface)
    {
        double StartZ=0,EndZ=0;
        if (!Height(*Surface,From.X,StartZ) || !Height(*Surface,To.X,EndZ)
            || FMath::Abs(From.Z-StartZ)>.01 || FMath::Abs(To.Z-EndZ)>.01)
        { Result.Reason=TEXT("native movement endpoints disagree with the signed floor surface");return Result; }
    }
    const auto Start=Ground(Pawn,From);
    Result.Overlaps.Append(Start.Overlaps);
    if (!Start.Clear) { Result.Reason=Start.Reason;Result.HitActor=Start.HitActor;Result.Diagnostic=Start.Diagnostic;return Result; }
    FWidthPawnRestore Restore(Pawn); auto* Movement=Pawn->GetCharacterMovement();
    Pawn->SetActorLocation(Start.Center,false,nullptr,ETeleportType::TeleportPhysics); Movement->SetMovementMode(MOVE_Walking);
    Movement->FindFloor(Start.Center,Movement->CurrentFloor,false);
    const int32 Steps=FMath::Max(1,FMath::CeilToInt(FVector::Dist2D(From,To)/MovementSpacingCm));
    for (int32 I=1;I<=Steps;++I)
    {
        FVector Seed=FMath::Lerp(From,To,double(I)/Steps);
        if (Surface && !Height(*Surface,Seed.X,Seed.Z))
        { Result.Reason=TEXT("native movement leaves the signed floor surface domain");return Result; }
        const auto Target=Ground(Pawn,Seed);
        Result.Overlaps.Append(Target.Overlaps);
        if (!Target.Clear) { Result.Reason=Target.Reason;Result.HitActor=Target.HitActor;Result.Diagnostic=Target.Diagnostic;return Result; }
        const FVector Delta(Seed.X-Pawn->GetActorLocation().X,Seed.Y-Pawn->GetActorLocation().Y,0);
        const FFindFloorResult PreviousFloor=Movement->CurrentFloor;
        FVector Ramp=WidthRampDelta(Movement,Delta,PreviousFloor.HitResult,PreviousFloor.bLineTrace);
        FHitResult Hit;
        Movement->SafeMoveUpdatedComponent(Ramp,Pawn->GetActorQuat(),true,Hit);
        double Applied=Hit.Time;
        // Match MoveAlongFloor's second ramp sweep before treating contact as a step.
        // Sliding out of this signed lane still fails the final position check.
        if (!Hit.bStartPenetrating && Hit.IsValidBlockingHit() && Hit.Time>0
            && Hit.Normal.Z>KINDA_SMALL_NUMBER && Movement->IsWalkable(Hit))
        {
            const double Remaining=1-Applied;
            Ramp=WidthRampDelta(Movement,Delta*Remaining,Hit,false);
            Movement->SafeMoveUpdatedComponent(Ramp,Pawn->GetActorQuat(),true,Hit);
            Applied=FMath::Clamp(Applied+Hit.Time*Remaining,0.,1.);
        }
        FStepDownResult Down;
        const auto FailureDiagnostic=[&]()
        {
            auto Row=MakeShared<FJsonObject>();Row->SetArrayField(TEXT("seed"),WidthVector(Seed));
            Row->SetArrayField(TEXT("center"),WidthVector(Pawn->GetActorLocation()));
            Row->SetArrayField(TEXT("attemptedDelta"),WidthVector(Delta));Row->SetArrayField(TEXT("lastRampDelta"),WidthVector(Ramp));
            Row->SetObjectField(TEXT("movementHit"),WidthHit(Hit));Row->SetObjectField(TEXT("previousFloor"),WidthFloor(PreviousFloor));
            Row->SetObjectField(TEXT("currentFloor"),WidthFloor(Movement->CurrentFloor));
            Row->SetObjectField(TEXT("capsuleContacts"),CapsuleContactDiagnostic(Pawn,Pawn->GetActorLocation()));
            Row->SetBoolField(TEXT("computedStepDownFloor"),Down.bComputedFloor);
            if (Down.bComputedFloor) Row->SetObjectField(TEXT("stepDownFloor"),WidthFloor(Down.FloorResult));
            return Row;
        };
        if (Hit.IsValidBlockingHit() || Hit.bStartPenetrating)
        {
            Result.StepAttempted=true; Result.HitActor=Hit.GetActor() ? Hit.GetActor()->GetName() : TEXT("");
            if (Hit.bStartPenetrating || !Movement->CanStepUp(Hit)
                || !Movement->StepUp(Movement->GetGravityDirection(),Delta*(1-Applied),Hit,&Down))
            { Result.Reason=TEXT("native swept movement cannot step past obstruction");Result.Diagnostic=FailureDiagnostic();return Result; }
            Result.StepSucceeded=true;
        }
        if (Down.bComputedFloor) Movement->CurrentFloor=Down.FloorResult;
        else Movement->FindFloor(Pawn->GetActorLocation(),Movement->CurrentFloor,false);
        const auto BeforeAdjustment=Movement->CurrentFloor;
        const FVector BeforeAdjustmentCenter=Pawn->GetActorLocation();
        Movement->AdjustFloorHeight();
        const FFindFloorResult Floor=Movement->CurrentFloor;
        const auto SupportEvidence=AdjustedSupport(Pawn,BeforeAdjustment,BeforeAdjustmentCenter,Floor,Pawn->GetActorLocation());
        Result.ActualCenter=Pawn->GetActorLocation(); ++Result.MovementSteps;
        const FString Obstruction=RoutePlacementObstruction(Pawn,Result.ActualCenter,Result.Overlaps,TEXT("native_movement_pose"));
        if (!Obstruction.IsEmpty()) { Result.Reason=TEXT("full capsule or headroom blocked during native movement");Result.HitActor=Obstruction;Result.Diagnostic=FailureDiagnostic();return Result; }
        if (!SupportEvidence.Verified || !Floor.IsWalkableFloor() || Floor.HitResult.bStartPenetrating
            || SupportEvidence.Distance<UCharacterMovementComponent::MIN_FLOOR_DIST-.1
            || SupportEvidence.Distance>UCharacterMovementComponent::MAX_FLOOR_DIST+.1
            || FMath::Abs(SupportEvidence.Impact.Z-Seed.Z)>MaxFloorDeviationCm)
        {
            Result.Reason=TEXT("native movement loses grounded walkable support");Result.Diagnostic=FailureDiagnostic();
            FFindFloorResult Fresh;Movement->FindFloor(Pawn->GetActorLocation(),Fresh,false);
            Result.Diagnostic->SetObjectField(TEXT("freshFloor"),WidthFloor(Fresh));
            if (SupportEvidence.Diagnostic) Result.Diagnostic->SetObjectField(TEXT("lineSupportVerification"),SupportEvidence.Diagnostic);
            return Result;
        }
        if (FVector::Dist2D(Result.ActualCenter,Seed)>1 || FMath::Abs(Result.ActualCenter.Z-Target.Center.Z)>2)
        { Result.Reason=TEXT("native movement deflected from the signed lane");Result.Diagnostic=FailureDiagnostic();return Result; }
    }
    Result.Clear=true;return Result;
}

bool UWarDutchBastionProof::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(),TEXT("WarDutchBastionProof"))
        && FParse::Param(FCommandLine::Get(),TEXT("WarDevelopmentGM"));
#endif
}
bool UWarDutchBastionProof::DoesSupportWorldType(EWorldType::Type Type) const { return Type==EWorldType::Game; }
TStatId UWarDutchBastionProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarDutchBastionProof,STATGROUP_Tickables); }

void UWarDutchBastionProof::HideArchitectureUi()
{
    // Screenshot's UI flag excludes Slate capture, but Canvas HUDs are already
    // rendered into the game framebuffer. Suppress both only during this proof.
    for (auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if (auto* Controller=It->Get();Controller && Controller->IsLocalController())
            if (auto* Hud=Controller->GetHUD())
            {
                if (!SavedHudVisibility.Contains(Hud))
                { const bool Previous=Hud->bShowHUD;SavedHudVisibility.Add(Hud,Previous); }
                Hud->bShowHUD=false;
            }
    TArray<UUserWidget*> Widgets;
    UWidgetBlueprintLibrary::GetAllWidgetsOfClass(GetWorld(),Widgets,UUserWidget::StaticClass(),true);
    for (auto* Widget:Widgets) if (Widget && Widget->IsInViewport() && Widget->GetWorld()==GetWorld())
    {
        if (!SavedWidgetVisibility.Contains(Widget)) SavedWidgetVisibility.Add(Widget,Widget->GetVisibility());
        Widget->SetVisibility(ESlateVisibility::Collapsed);
    }
    bArchitectureUiSuppressed=true;
}
void UWarDutchBastionProof::RestoreArchitectureUi()
{
    for (const auto& Pair:SavedHudVisibility) if (auto* Hud=Pair.Key.Get()) Hud->bShowHUD=Pair.Value;
    for (const auto& Pair:SavedWidgetVisibility) if (auto* Widget=Pair.Key.Get()) Widget->SetVisibility(Pair.Value);
    SavedHudVisibility.Reset();SavedWidgetVisibility.Reset();
}
void UWarDutchBastionProof::Deinitialize()
{ RestoreArchitectureUi();Super::Deinitialize(); }

void UWarDutchBastionProof::Finish(bool Passed,const FString& Detail)
{
    bFinished=true;
    RestoreArchitectureUi();
    Passed=Passed && bPhysicalPassed && (!bCitadelWidth || (bWidthComplete && bWidthPassed));
    auto Report=MakeShared<FJsonObject>();
    const bool WidthDiagnostic=FParse::Param(FCommandLine::Get(),TEXT("WarCitadelWidthDiagnostic"));
    Report->SetBoolField(TEXT("diagnosticOnly"),WidthDiagnostic);
    Report->SetBoolField(TEXT("passed"),Passed);Report->SetStringField(TEXT("detail"),Detail);
    Report->SetStringField(TEXT("signature"),Signature);Report->SetStringField(TEXT("map"),GetWorld()->GetOutermost()->GetName());
    Report->SetNumberField(TEXT("views"),ViewIndex);Report->SetNumberField(TEXT("routesWalked"),RouteIndex);
    Report->SetArrayField(TEXT("routeFailures"),RouteFailures);
    Report->SetArrayField(TEXT("completedRoutes"),CompletedRoutes);
    Report->SetArrayField(TEXT("gateSweeps"),GateSweeps);
    Report->SetArrayField(TEXT("gateVerticalSweeps"),GateVerticalSweeps);
    Report->SetArrayField(TEXT("objectiveSamples"),ObjectiveSamples);
    Report->SetArrayField(TEXT("spawnSamples"),SpawnSamples);
    Report->SetArrayField(TEXT("physicalFailures"),PhysicalFailures);
    Report->SetBoolField(TEXT("routeWidthComplete"),bWidthComplete);
    Report->SetBoolField(TEXT("routeWidthPassed"),bCitadelWidth && bWidthComplete && bWidthPassed);
    Report->SetArrayField(TEXT("routeWidthSamples"),RouteWidthSamples);
    if (RouteWidthConfig) Report->SetObjectField(TEXT("routeWidthConfig"),RouteWidthConfig);
    Report->SetStringField(TEXT("cityRevision"),CityRevision);
    Report->SetStringField(TEXT("mapSha256"),MapSha256);
    Report->SetArrayField(TEXT("viewPerformance"),ViewPerformance);
    Report->SetBoolField(TEXT("architectureUiSuppressed"),bArchitectureUiSuppressed);
    Report->SetBoolField(TEXT("visualApproved"),false);Report->SetBoolField(TEXT("citywideAcceptance"),false);
    Report->SetBoolField(TEXT("releaseAcceptance"),false);
    if (auto* PC=GetWorld()->GetFirstPlayerController())
        if (auto* Pawn=Cast<AWarCharacter>(PC->GetPawn()))
        {
            Report->SetNumberField(TEXT("capsuleRadiusCm"),Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius());
            Report->SetNumberField(TEXT("capsuleHeightCm"),Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()*2);
        }
    Frames.Sort();Report->SetNumberField(TEXT("frameSamples"),Frames.Num());
    if (!Frames.IsEmpty()) Report->SetNumberField(TEXT("p95FrameMs"),Frames[FMath::Min(Frames.Num()-1,FMath::FloorToInt(Frames.Num()*.95))]);
    DrawCalls.Sort();Primitives.Sort();
    if (!DrawCalls.IsEmpty()) Report->SetNumberField(TEXT("p95DrawCalls"),DrawCalls[FMath::Min(DrawCalls.Num()-1,FMath::FloorToInt(DrawCalls.Num()*.95))]);
    if (!Primitives.IsEmpty()) Report->SetNumberField(TEXT("p95Primitives"),Primitives[FMath::Min(Primitives.Num()-1,FMath::FloorToInt(Primitives.Num()*.95))]);
    Report->SetNumberField(TEXT("peakStreamingRequestsAfterSettle"),PeakStreamingRequests);
    Report->SetNumberField(TEXT("usedPhysicalMiB"),FPlatformMemory::GetStats().UsedPhysical/1048576.0);
    if (auto* Limit=IConsoleManager::Get().FindConsoleVariable(TEXT("t.MaxFPS"))) Report->SetNumberField(TEXT("frameLimit"),Limit->GetFloat());
    if (auto* VSync=IConsoleManager::Get().FindConsoleVariable(TEXT("r.VSync"))) Report->SetNumberField(TEXT("vSync"),VSync->GetInt());
    if (!WarCitadelProofJson::Save(Report,Directory/TEXT("report.json")))
    {
        UE_LOG(LogTemp,Error,TEXT("Cannot write complete native citadel proof report"));
        FPlatformMisc::RequestExitWithStatus(false,1);return;
    }
    UE_LOG(LogTemp,Display,TEXT("WAR_DUTCH_PROOF=%s %s"),Passed?TEXT("PASS"):TEXT("FAIL"),*Detail);
    FPlatformMisc::RequestExitWithStatus(false,Passed || (WidthDiagnostic && bWidthComplete) ? 0 : 1);
}

bool UWarDutchBastionProof::MatchesCapturedKinematics(const AWarCharacter* Pawn) const
{
    return !bCitadelConfig || (KinematicsBaseline && KinematicsBaseline->Matches(Pawn));
}

void UWarDutchBastionProof::Tick(float DeltaTime)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now=GetWorld()->GetTimeSeconds();if (Started<0) Started=Now;
    if (!bInitialized)
    {
        FString Text;TSharedPtr<FJsonObject> Config;
        Directory=FPaths::ProjectSavedDir()/TEXT("DutchBastion");IFileManager::Get().MakeDirectory(*Directory,true);
        FString ConfigPath=FPaths::ProjectContentDir()/TEXT("Migration/dutch-bastion-proof.json");
        const bool Citadel=FParse::Value(FCommandLine::Get(),TEXT("WarCitadelProofConfig="),ConfigPath);
        bCitadelConfig=Citadel;
        if (Citadel)
        {
            ConfigPath=FPaths::ConvertRelativePathToFull(ConfigPath);
            FString Saved=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());
            FPaths::NormalizeDirectoryName(Saved); FPaths::NormalizeFilename(ConfigPath);
            if (!ConfigPath.StartsWith(Saved+TEXT("/")))
            { Finish(false,TEXT("Citadel proof configuration must be under project Saved"));return; }
            Directory=FPaths::GetPath(ConfigPath);
        }
        if (!FFileHelper::LoadFileToString(Text,*ConfigPath)
            || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Config) || !Config.IsValid())
        { Finish(false,TEXT("Missing architecture proof configuration"));return; }
        const FString Map=GetWorld()->GetOutermost()->GetName();
        if ((!Map.StartsWith(TEXT("/Game/WorldRebuild/DutchBastion_"))
                && !(Citadel && Map.StartsWith(TEXT("/Game/WorldRebuild/AegisCitadel_"))))
            || Map!=Config->GetStringField(TEXT("map")))
        { Finish(false,TEXT("Proof requires its exact isolated revision"));return; }
        Signature=Config->GetStringField(TEXT("signature"));
        Config->TryGetStringField(TEXT("cityRevision"),CityRevision);
        Config->TryGetStringField(TEXT("mapSha256"),MapSha256);
        if (Config->TryGetNumberField(TEXT("viewSettleSeconds"),ViewSettleSeconds)) ViewSettleSeconds=FMath::Clamp(ViewSettleSeconds,3.0,30.0);
        Views=Config->GetArrayField(TEXT("views"));Routes=Config->GetArrayField(TEXT("routes"));
        bCitadelWidth=Citadel && !Routes.IsEmpty();
        const TArray<TSharedPtr<FJsonValue>>* ConfigGates=nullptr;
        if (Citadel && Config->TryGetArrayField(TEXT("gates"),ConfigGates)) Gates=*ConfigGates;
        const TArray<TSharedPtr<FJsonValue>>* ConfigAnchors=nullptr;
        if (Citadel && Config->TryGetArrayField(TEXT("anchors"),ConfigAnchors)) Anchors=*ConfigAnchors;
        const TArray<TSharedPtr<FJsonValue>>* ConfigSpawnPads=nullptr;
        if (Citadel && Config->TryGetArrayField(TEXT("spawnPads"),ConfigSpawnPads)) SpawnPads=*ConfigSpawnPads;
        bInitialized=true;
    }
    auto* PC=GetWorld()->GetFirstPlayerController();auto* Pawn=PC?Cast<AWarCharacter>(PC->GetPawn()):nullptr;
    if (!Pawn || !Pawn->IsVisualReady())
    { if (Now-Started>60) Finish(false,TEXT("Playable character unavailable"));return; }
    if (bCitadelConfig && !WarCitadelCapsulePolicy::Matches(Pawn))
    { Finish(false,TEXT("Proof character capsule differs from the reviewed native class default"));return; }
    if (bCitadelConfig)
    {
        if (!KinematicsBaseline) KinematicsBaseline=MakeShared<WarCitadelCapsulePolicy::FKinematicsBaseline>(Pawn);
        if (!KinematicsBaseline->Matches(Pawn))
        { Finish(false,TEXT("Proof character geometry or walking limits changed after baseline capture"));return; }
    }
    if (bCitadelConfig && !bCityBindingChecked)
    {
        const AWarSiegeBattlefield* Field=nullptr;
        for (TActorIterator<AWarSiegeBattlefield> It(GetWorld());It;++It)
        { if (Field) { Finish(false,TEXT("Duplicate candidate battlefield"));return; }Field=*It; }
        FString Error;
        if (!Field || !Field->CityDefinition || !Field->CityDefinition->Validate(Error)
            || CityRevision.IsEmpty() || Field->CityDefinition->Revision!=CityRevision)
        { Finish(false,TEXT("Candidate native city definition differs from its requested revision: ")+Error);return; }
        bCityBindingChecked=true;
    }
    if (!bGatesTested && !Gates.IsEmpty())
    {
        AWarSiegeBattlefield* Battlefield=nullptr;
        for (TActorIterator<AWarSiegeBattlefield> It(GetWorld());It;++It)
        { if (Battlefield) { Finish(false,TEXT("Duplicate candidate battlefield"));return; } Battlefield=*It; }
        if (!Battlefield || Battlefield->StageGates.Num()!=2)
        { Finish(false,TEXT("Candidate must have both physical stage cuts"));return; }
        // Sweep the actual playable capsule at the center and both aperture
        // edges, in both directions, through all three milestone states.
        // These are unsaved physical fixtures and never grant review flags.
        const float Radius=Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius();
        const float HalfHeight=Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        const uint8 ClaimsByPhase[]={0,8,127};
        for (int32 Phase=0;Phase<3;++Phase)
        {
            FWarSiegeState State;State.Phase=EWarSiegePhase::Active;State.MainClaims=ClaimsByPhase[Phase];
            State.Stage=Phase==2 ? 2 : 0;Battlefield->ApplyMilestones(State);
            for (const auto& Value:Gates)
            {
                const auto Gate=Value->AsObject();const int32 Index=int32(Gate->GetNumberField(TEXT("index")));
                if (!Battlefield->StageGates.IsValidIndex(Index) || !IsValid(Battlefield->StageGates[Index]))
                { Finish(false,TEXT("Missing physical gate actor"));return; }
                const FVector Feet=Point(Gate->GetArrayField(TEXT("point")));
                const double Edge=Gate->GetNumberField(TEXT("width"))*.5-Radius-5;
                const double Height=Gate->GetNumberField(TEXT("height"));
                if (Edge<0 || !FMath::IsFinite(Height) || Height<HalfHeight*2+6)
                { Finish(false,TEXT("Gate aperture smaller than equipped capsule"));return; }
                double SweepSpan=400;Gate->TryGetNumberField(TEXT("sweepHalfSpanCm"),SweepSpan);
                FVector GateCenter,GateExtent;Battlefield->StageGates[Index]->GetActorBounds(false,GateCenter,GateExtent);
                if (!FMath::IsFinite(SweepSpan) || SweepSpan>400 || GateCenter.ContainsNaN() || GateExtent.ContainsNaN() || GateExtent.X<=0
                    || FMath::Abs(GateCenter.X-Feet.X)>.01 || SweepSpan<=GateExtent.X+Radius+3)
                { Finish(false,TEXT("Gate sweep does not clear its actual leaf and capsule"));return; }
                const TSharedPtr<FJsonObject>* Approach=nullptr;
                if (Gate->TryGetObjectField(TEXT("approachClearance"),Approach))
                {
                    const double Incoming=(*Approach)->GetNumberField(TEXT("incomingFlatLengthCm"));
                    const double Outgoing=(*Approach)->GetNumberField(TEXT("outgoingFlatLengthCm"));
                    const double Margin=(*Approach)->GetNumberField(TEXT("requiredCapsuleFloorMarginCm"));
                    const double MaximumThickness=(*Approach)->GetNumberField(TEXT("maximumLeafHalfThicknessCm"));
                    if (!FMath::IsFinite(Incoming) || !FMath::IsFinite(Outgoing) || !FMath::IsFinite(Margin)
                        || !FMath::IsFinite(MaximumThickness) || Margin<3 || GateExtent.X>MaximumThickness+.01
                        || SweepSpan+Radius+Margin>FMath::Min(Incoming,Outgoing)+.01)
                    { Finish(false,TEXT("Actual gate capsule exceeds the signed flat approach landing"));return; }
                }
                const bool Closed=Phase==0 || (Phase==1 && Index==1);
                for (int32 Lane=-1;Lane<=1;++Lane) for (int32 Direction : {-1,1})
                {
                    const FVector Center=Feet+FVector(0,Lane*Edge,HalfHeight+3);
                    FCollisionQueryParams Query(SCENE_QUERY_STAT(CitadelGateSweep),true,Pawn);
                    FHitResult Hit;
                    const FVector Start=Center+FVector(-Direction*SweepSpan,0,0),End=Center+FVector(Direction*SweepSpan,0,0);
                    const bool StartClear=CapsuleObstruction(Pawn,Start).IsEmpty(),EndClear=CapsuleObstruction(Pawn,End).IsEmpty();
                    const bool Blocked=GetWorld()->SweepSingleByChannel(Hit,Start,End,FQuat::Identity,ECC_Pawn,
                        FCollisionShape::MakeCapsule(Radius,HalfHeight),Query);
                    const bool Passed=StartClear && EndClear && !Hit.bStartPenetrating
                        && (Closed ? Blocked && Hit.GetActor()==Battlefield->StageGates[Index] : !Blocked);
                    auto Evidence=MakeShared<FJsonObject>();
                    Evidence->SetStringField(TEXT("id"),Gate->GetStringField(TEXT("id")));
                    Evidence->SetNumberField(TEXT("phase"),Phase);Evidence->SetNumberField(TEXT("lane"),Lane);
                    Evidence->SetNumberField(TEXT("direction"),Direction);Evidence->SetBoolField(TEXT("closed"),Closed);
                    Evidence->SetBoolField(TEXT("blocked"),Blocked);Evidence->SetBoolField(TEXT("passed"),Passed);
                    Evidence->SetStringField(TEXT("hitActor"),Hit.GetActor()?Hit.GetActor()->GetName():TEXT(""));
                    Evidence->SetBoolField(TEXT("startClear"),StartClear);Evidence->SetBoolField(TEXT("endClear"),EndClear);
                    Evidence->SetNumberField(TEXT("sweepHalfSpanCm"),SweepSpan);
                    Evidence->SetNumberField(TEXT("actualLeafHalfThicknessCm"),GateExtent.X);
                    GateSweeps.Add(MakeShared<FJsonValueObject>(Evidence));
                    if (!Passed)
                    {
                        auto Failure=MakeShared<FJsonObject>();Failure->SetStringField(TEXT("id"),Gate->GetStringField(TEXT("id")));
                        Failure->SetStringField(TEXT("reason"),TEXT("A stage gate leaks collision or an open aperture is obstructed"));
                        PhysicalFailures.Add(MakeShared<FJsonValueObject>(Failure));bPhysicalPassed=false;
                    }
                }
                // Raised approaches must not reach an unblocked opening above a short leaf.
                // Sweep the actual capsule through three elevations within the full aperture.
                for (int32 Level=1;Level<=3;++Level) for (int32 Direction : {-1,1})
                {
                    const double Offset=HalfHeight+3+(Height-HalfHeight*2-6)*Level/4;
                    const FVector Center=Feet+FVector(0,0,Offset);
                    FCollisionQueryParams Query(SCENE_QUERY_STAT(CitadelElevatedGateSweep),true,Pawn);FHitResult Hit;
                    const FVector Start=Center+FVector(-Direction*SweepSpan,0,0),End=Center+FVector(Direction*SweepSpan,0,0);
                    const bool StartClear=CapsuleObstruction(Pawn,Start).IsEmpty(),EndClear=CapsuleObstruction(Pawn,End).IsEmpty();
                    const bool Blocked=GetWorld()->SweepSingleByChannel(Hit,Start,End,FQuat::Identity,ECC_Pawn,
                        FCollisionShape::MakeCapsule(Radius,HalfHeight),Query);
                    const bool Passed=StartClear && EndClear && !Hit.bStartPenetrating
                        && (Closed ? Blocked && Hit.GetActor()==Battlefield->StageGates[Index] : !Blocked);
                    auto Evidence=MakeShared<FJsonObject>();Evidence->SetStringField(TEXT("id"),Gate->GetStringField(TEXT("id")));
                    Evidence->SetNumberField(TEXT("phase"),Phase);Evidence->SetNumberField(TEXT("level"),Level);
                    Evidence->SetNumberField(TEXT("direction"),Direction);Evidence->SetNumberField(TEXT("heightCm"),Height);
                    Evidence->SetNumberField(TEXT("centerOffsetCm"),Offset);Evidence->SetNumberField(TEXT("capsuleHalfHeightCm"),HalfHeight);
                    Evidence->SetBoolField(TEXT("closed"),Closed);Evidence->SetBoolField(TEXT("blocked"),Blocked);
                    Evidence->SetBoolField(TEXT("passed"),Passed);
                    Evidence->SetStringField(TEXT("hitActor"),Hit.GetActor()?Hit.GetActor()->GetName():TEXT(""));
                    Evidence->SetBoolField(TEXT("startClear"),StartClear);Evidence->SetBoolField(TEXT("endClear"),EndClear);
                    Evidence->SetNumberField(TEXT("sweepHalfSpanCm"),SweepSpan);
                    Evidence->SetNumberField(TEXT("actualLeafHalfThicknessCm"),GateExtent.X);
                    GateVerticalSweeps.Add(MakeShared<FJsonValueObject>(Evidence));
                    if (!Passed)
                    {
                        auto Failure=MakeShared<FJsonObject>();Failure->SetStringField(TEXT("id"),Gate->GetStringField(TEXT("id")));
                        Failure->SetStringField(TEXT("reason"),TEXT("An elevated approach bypasses a closed gate or the open portal is obstructed"));
                        PhysicalFailures.Add(MakeShared<FJsonValueObject>(Failure));bPhysicalPassed=false;
                    }
                }
            }
        }
        bGatesTested=true;
    }
    if (!bAnchorsTested && !Anchors.IsEmpty())
    {
        AWarSiegeBattlefield* Battlefield=nullptr;
        for (TActorIterator<AWarSiegeBattlefield> It(GetWorld());It;++It)
        { if (Battlefield) { Finish(false,TEXT("Duplicate candidate battlefield"));return; } Battlefield=*It; }
        if (!Battlefield || Anchors.Num()!=11)
        { Finish(false,TEXT("All physical objective anchors are required"));return; }
        const auto* Capsule=Pawn->GetCapsuleComponent();
        const double Radius=Capsule->GetScaledCapsuleRadius(),Half=Capsule->GetScaledCapsuleHalfHeight();
        for (const auto& Value:Anchors)
        {
            const auto Anchor=Value->AsObject(); const bool Optional=Anchor->GetBoolField(TEXT("optional"));
            const int32 Index=int32(Anchor->GetNumberField(TEXT("index")));
            const auto& Locations=Optional ? Battlefield->OptionalObjectives : Battlefield->Objectives;
            const FVector Location=Point(Anchor->GetArrayField(TEXT("point")));
            if (!Locations.IsValidIndex(Index) || !Locations[Index].Equals(Location,.001))
            { Finish(false,TEXT("Native objective position differs from its signed ledger"));return; }
            int32 Playable=0;
            for (int32 Spoke=0;Spoke<8;++Spoke)
            {
                const double Angle=Spoke*PI/4;
                const FVector Seed=Location+FVector(FMath::Cos(Angle),FMath::Sin(Angle),0)*450;
                FCollisionQueryParams Query(SCENE_QUERY_STAT(CitadelObjectiveFloor),false,Pawn);FHitResult Floor,Sight;
                const bool FloorFound=GetWorld()->LineTraceSingleByObjectType(Floor,Seed+FVector(0,0,400),Seed-FVector(0,0,400),
                    FCollisionObjectQueryParams(ECC_WorldStatic),Query) && Floor.ImpactNormal.Z>=.7;
                const FVector Center=Floor.ImpactPoint+FVector(0,0,Half-Radius+Radius/FMath::Max(.7,double(Floor.ImpactNormal.Z))+3);
                const bool OnCaptureFloor=FloorFound && FMath::Abs(Center.Z-Location.Z)<250;
                const bool Clear=OnCaptureFloor && !GetWorld()->OverlapBlockingTestByChannel(Center,FQuat::Identity,ECC_Pawn,
                    FCollisionShape::MakeCapsule(Radius,Half),Query);
                const bool Blocked=Clear && GetWorld()->LineTraceSingleByChannel(Sight,Center,Location+FVector(0,0,100),ECC_Visibility,Query);
                const bool Target=Optional && Battlefield->WarEffortProps.IsValidIndex(Index)
                    && IsValid(Battlefield->WarEffortProps[Index]) && Sight.GetActor()==Battlefield->WarEffortProps[Index];
                const bool Visible=Clear && (!Blocked || Target);
                auto Evidence=MakeShared<FJsonObject>();Evidence->SetStringField(TEXT("id"),Anchor->GetStringField(TEXT("id")));
                Evidence->SetNumberField(TEXT("spoke"),Spoke);Evidence->SetBoolField(TEXT("floor"),OnCaptureFloor);
                Evidence->SetBoolField(TEXT("capsuleClear"),Clear);Evidence->SetBoolField(TEXT("lineOfSight"),Visible);
                Evidence->SetStringField(TEXT("floorActor"),Floor.GetActor()?Floor.GetActor()->GetName():TEXT(""));
                Evidence->SetStringField(TEXT("sightActor"),Sight.GetActor()?Sight.GetActor()->GetName():TEXT(""));
                ObjectiveSamples.Add(MakeShared<FJsonValueObject>(Evidence));Playable+=Visible ? 1 : 0;
            }
            if (Playable<4)
            {
                auto Failure=MakeShared<FJsonObject>();Failure->SetStringField(TEXT("id"),Anchor->GetStringField(TEXT("id")));
                Failure->SetStringField(TEXT("reason"),TEXT("Objective lacks four clear capture positions with line of sight"));
                PhysicalFailures.Add(MakeShared<FJsonValueObject>(Failure));bPhysicalPassed=false;
            }
        }
        if (!SpawnPads.IsEmpty())
        {
            if (SpawnPads.Num()!=Battlefield->TeamSpawns.Num())
            { Finish(false,TEXT("Every retained spawn needs its signed native pad proof"));return; }
            TSet<int32> Tested;
            for (const auto& Value:SpawnPads)
            {
                const auto Pad=Value->AsObject();
                const auto& Values=Pad->GetArrayField(TEXT("point"));
                const FVector Location=Point(Values);
                const int32 Index=int32(Pad->GetNumberField(TEXT("index")));
                const double Width=Pad->GetNumberField(TEXT("widthCm"));
                FVector2D Gradient=FVector2D::ZeroVector;
                const TArray<TSharedPtr<FJsonValue>>* Slope=nullptr;
                if (Pad->TryGetArrayField(TEXT("groundGradient"),Slope))
                {
                    if (Slope->Num()!=2 || (*Slope)[0]->Type!=EJson::Number || (*Slope)[1]->Type!=EJson::Number)
                    { Finish(false,TEXT("Spawn ground gradient requires two numeric coordinates"));return; }
                    Gradient=FVector2D((*Slope)[0]->AsNumber(),(*Slope)[1]->AsNumber());
                }
                if (Values.Num()!=3 || Location.ContainsNaN() || !Battlefield->TeamSpawns.IsValidIndex(Index)
                    || Tested.Contains(Index) || !Battlefield->TeamSpawns[Index].Equals(Location,.01)
                    || !FMath::IsFinite(Width) || Width<600)
                { Finish(false,TEXT("Spawn pad does not match its actual retained anchor"));return; }
                Tested.Add(Index);
                for (int32 X=-2;X<=2;++X) for (int32 Y=-2;Y<=2;++Y)
                {
                    FVector Seed,Center;
                    if (!WarCitadelRouteWidth::SpawnPadSeed(Location,Width,Radius,Index,X,Y,Gradient,Seed))
                    { Finish(false,TEXT("Spawn pad ground surface is invalid"));return; }
                    const bool Clear=WarSiegeNavigation::SpawnCandidate(GetWorld(),Seed,Radius,Half,Center,Pawn);
                    auto Evidence=MakeShared<FJsonObject>();Evidence->SetNumberField(TEXT("index"),Index);
                    Evidence->SetNumberField(TEXT("x"),X);Evidence->SetNumberField(TEXT("y"),Y);
                    Evidence->SetArrayField(TEXT("seed"),{MakeShared<FJsonValueNumber>(Seed.X),
                        MakeShared<FJsonValueNumber>(Seed.Y),MakeShared<FJsonValueNumber>(Seed.Z)});
                    Evidence->SetBoolField(TEXT("clear"),Clear);SpawnSamples.Add(MakeShared<FJsonValueObject>(Evidence));
                    if (!Clear)
                    {
                        auto Failure=MakeShared<FJsonObject>();Failure->SetStringField(TEXT("id"),FString::Printf(TEXT("spawn:%d:%d:%d"),Index,X,Y));
                        Failure->SetStringField(TEXT("reason"),TEXT("Retained spawn pad fails actual floor or capsule clearance"));
                        PhysicalFailures.Add(MakeShared<FJsonValueObject>(Failure));bPhysicalPassed=false;
                    }
                }
            }
        }
        bAnchorsTested=true;
    }
    if (bCitadelWidth && !bWidthComplete)
    {
        const auto* Capsule=Pawn->GetCapsuleComponent(); const auto* Movement=Pawn->GetCharacterMovement();
        const double Radius=Capsule->GetScaledCapsuleRadius(),Half=Capsule->GetScaledCapsuleHalfHeight();
        if (!RouteWidthConfig)
        {
            RouteWidthConfig=MakeShared<FJsonObject>();
            RouteWidthConfig->SetNumberField(TEXT("version"),4);
            RouteWidthConfig->SetObjectField(TEXT("capsuleCollisionPolicy"),WarCitadelCapsulePolicy::Readback(Pawn));
            auto Kinematics=WarCitadelCapsulePolicy::KinematicsReadback(Pawn);
            Kinematics->SetBoolField(TEXT("capturedRuntimeValuesPinned"),KinematicsBaseline && KinematicsBaseline->Matches(Pawn));
            RouteWidthConfig->SetObjectField(TEXT("capsuleKinematicsPolicy"),Kinematics);
            RouteWidthConfig->SetBoolField(TEXT("capsulePolicyCheckedEveryTick"),true);
            RouteWidthConfig->SetBoolField(TEXT("capsulePolicyCheckedEveryPlacementQuery"),true);
            RouteWidthConfig->SetStringField(TEXT("placementOverlapPolicy"),TEXT("fresh_live_static_single_body_unit_zero_margin_full_capsule_planes_v1"));
            RouteWidthConfig->SetBoolField(TEXT("gateOverlapAdmissionRemainsRaw"),true);
            RouteWidthConfig->SetArrayField(TEXT("laneFractions"),{MakeShared<FJsonValueNumber>(-1),MakeShared<FJsonValueNumber>(-.5),
                MakeShared<FJsonValueNumber>(0),MakeShared<FJsonValueNumber>(.5),MakeShared<FJsonValueNumber>(1)});
            RouteWidthConfig->SetNumberField(TEXT("maxSpacingCm"),WarCitadelRouteWidth::MaxSpacingCm);
            RouteWidthConfig->SetNumberField(TEXT("movementSpacingCm"),WarCitadelRouteWidth::MovementSpacingCm);
            RouteWidthConfig->SetNumberField(TEXT("edgeInsetCm"),0);
            RouteWidthConfig->SetNumberField(TEXT("maxFloorDeviationCm"),WarCitadelRouteWidth::MaxFloorDeviationCm);
            RouteWidthConfig->SetNumberField(TEXT("groundClearanceCm"),WarCitadelRouteWidth::GroundClearanceCm);
            RouteWidthConfig->SetNumberField(TEXT("minFloorDistanceCm"),UCharacterMovementComponent::MIN_FLOOR_DIST);
            RouteWidthConfig->SetNumberField(TEXT("maxFloorDistanceCm"),UCharacterMovementComponent::MAX_FLOOR_DIST);
            RouteWidthConfig->SetNumberField(TEXT("capsuleRadiusCm"),Radius);
            RouteWidthConfig->SetNumberField(TEXT("capsuleHalfHeightCm"),Half);
            RouteWidthConfig->SetNumberField(TEXT("maxStepHeightCm"),Movement->MaxStepHeight);
            RouteWidthConfig->SetNumberField(TEXT("walkableFloorZ"),Movement->GetWalkableFloorZ());
            RouteWidthConfig->SetStringField(TEXT("collisionChannel"),TEXT("ECC_Pawn"));
            RouteWidthConfig->SetStringField(TEXT("collisionProfile"),Capsule->GetCollisionProfileName().ToString());
            RouteWidthConfig->SetBoolField(TEXT("simpleCollision"),true);
            RouteWidthConfig->SetStringField(TEXT("movementMethod"),TEXT("ComputeGroundMovementDelta/ramp-resweep/StepUp-floor-handoff/FindFloor/AdjustFloorHeight"));
            RouteWidthConfig->SetStringField(TEXT("surfaceSamplingMethod"),TEXT("signed_world_x_piecewise_linear_per_lane_and_movement_step"));
            TArray<TSharedPtr<FJsonValue>> Profiles;
            for (const auto& RouteValue:Routes)
            {
                const auto Row=RouteValue->AsObject();
                if (!Row->HasField(TEXT("surfaceProfile"))) continue;
                const TSharedPtr<FJsonObject>* Profile=nullptr;WarCitadelRouteWidth::FSurface Parsed;
                if (!Row->TryGetObjectField(TEXT("surfaceProfile"),Profile)
                    || !WarCitadelRouteWidth::ReadSurface(*Profile,Row->GetStringField(TEXT("id")),Parsed))
                { Finish(false,TEXT("Signed route has an invalid authored floor surface"));return; }
                auto Witness=MakeShared<FJsonObject>();Witness->SetStringField(TEXT("id"),Row->GetStringField(TEXT("id")));
                Witness->SetObjectField(TEXT("surfaceProfile"),*Profile);Profiles.Add(MakeShared<FJsonValueObject>(Witness));
            }
            RouteWidthConfig->SetArrayField(TEXT("surfaceProfiles"),Profiles);
        }
        const auto WidthRoute=Routes[WidthRouteIndex]->AsObject();
        const auto WidthPoints=WidthRoute->GetArrayField(TEXT("points")); double Width=0;
        if (WidthPoints.Num()<2 || !WidthRoute->TryGetNumberField(TEXT("clearWidthCm"),Width) || !FMath::IsFinite(Width))
        { Finish(false,TEXT("Signed route lacks valid width or segments"));return; }
        WarCitadelRouteWidth::FSurface Surface;const WarCitadelRouteWidth::FSurface* SurfacePtr=nullptr;
        if (WidthRoute->HasField(TEXT("surfaceProfile")))
        {
            const TSharedPtr<FJsonObject>* Profile=nullptr;
            if (!WidthRoute->TryGetObjectField(TEXT("surfaceProfile"),Profile)
                || !WarCitadelRouteWidth::ReadSurface(*Profile,WidthRoute->GetStringField(TEXT("id")),Surface))
            { Finish(false,TEXT("Signed width route has invalid floor surface math"));return; }
            SurfacePtr=&Surface;
        }
        const double Lanes[]={-1,-.5,0,.5,1}; FVector Previous[5]; bool HavePrevious[5]={}; bool RoutePassed=true;
        const auto VectorJson=[](const FVector& Value)
        { return TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(Value.X),MakeShared<FJsonValueNumber>(Value.Y),MakeShared<FJsonValueNumber>(Value.Z)}; };
        for (int32 Segment=0;Segment<WidthPoints.Num()-1;++Segment)
        {
            const FVector From=Point(WidthPoints[Segment]->AsArray()),To=Point(WidthPoints[Segment+1]->AsArray());
            const int32 Count=WarCitadelRouteWidth::Intervals(From,To);
            if (!Count) { Finish(false,TEXT("Signed width route has invalid or vertical-only segment"));return; }
            for (int32 SampleIndex=0;SampleIndex<=Count;++SampleIndex) for (int32 LaneIndex=0;LaneIndex<5;++LaneIndex)
            {
                FVector Seed; double Offset=0;
                if (!WarCitadelRouteWidth::Sample(From,To,Width,Radius,SampleIndex,Lanes[LaneIndex],Seed,Offset,SurfacePtr))
                { Finish(false,TEXT("Signed width route is smaller than the native capsule or has invalid sample math"));return; }
                const auto Placement=WarCitadelRouteWidth::Ground(Pawn,Seed);
                WarCitadelRouteWidth::FTransition Transition;
                if (Placement.Clear && HavePrevious[LaneIndex])
                    Transition=WarCitadelRouteWidth::Traverse(Pawn,Previous[LaneIndex],Seed,SurfacePtr);
                else if (Placement.Clear) Transition.Clear=true;
                else { Transition.Reason=Placement.Reason;Transition.HitActor=Placement.HitActor; }
                const bool Passed=Placement.Floor && Placement.Clear && Transition.Clear
                    && (!Transition.StepAttempted || Transition.StepSucceeded);
                auto Evidence=MakeShared<FJsonObject>();
                Evidence->SetObjectField(TEXT("placementOverlapEvidence"),Placement.Overlaps.Json());
                Evidence->SetObjectField(TEXT("movementOverlapEvidence"),Transition.Overlaps.Json());
                Evidence->SetStringField(TEXT("id"),WidthRoute->GetStringField(TEXT("id")));
                Evidence->SetNumberField(TEXT("segment"),Segment);Evidence->SetNumberField(TEXT("sample"),SampleIndex);
                Evidence->SetNumberField(TEXT("lane"),Lanes[LaneIndex]);Evidence->SetNumberField(TEXT("alpha"),double(SampleIndex)/Count);
                Evidence->SetNumberField(TEXT("clearWidthCm"),Width);Evidence->SetNumberField(TEXT("lateralOffsetCm"),Offset);
                Evidence->SetArrayField(TEXT("seed"),VectorJson(Seed));Evidence->SetArrayField(TEXT("center"),VectorJson(Placement.Center));
                Evidence->SetArrayField(TEXT("floorImpact"),VectorJson(Placement.FloorImpact));
                Evidence->SetNumberField(TEXT("floorZCm"),Placement.FloorImpact.Z);
                Evidence->SetNumberField(TEXT("floorNormalZ"),Placement.FloorNormalZ);
                Evidence->SetNumberField(TEXT("floorDistanceCm"),Placement.FloorDistance);
                Evidence->SetBoolField(TEXT("floor"),Placement.Floor);Evidence->SetBoolField(TEXT("placementClear"),Placement.Clear);
                Evidence->SetBoolField(TEXT("transitionClear"),Transition.Clear);Evidence->SetBoolField(TEXT("passed"),Passed);
                Evidence->SetBoolField(TEXT("stepAttempted"),Transition.StepAttempted);Evidence->SetBoolField(TEXT("stepSucceeded"),Transition.StepSucceeded);
                Evidence->SetNumberField(TEXT("movementSteps"),Transition.MovementSteps);
                Evidence->SetStringField(TEXT("reason"),Placement.Clear ? Transition.Reason : Placement.Reason);
                Evidence->SetStringField(TEXT("floorActor"),Placement.FloorActor);
                Evidence->SetStringField(TEXT("hitActor"),Placement.Clear ? Transition.HitActor : Placement.HitActor);
                if (Placement.Diagnostic) Evidence->SetObjectField(TEXT("destinationDiagnostic"),Placement.Diagnostic);
                if (Transition.Diagnostic) Evidence->SetObjectField(TEXT("failedSubstepDiagnostic"),Transition.Diagnostic);
                RouteWidthSamples.Add(MakeShared<FJsonValueObject>(Evidence)); RoutePassed&=Passed;
                Previous[LaneIndex]=Seed;HavePrevious[LaneIndex]=true;
            }
        }
        if (!RoutePassed)
        {
            auto Failure=MakeShared<FJsonObject>();Failure->SetStringField(TEXT("id"),WidthRoute->GetStringField(TEXT("id")));
            Failure->SetStringField(TEXT("reason"),TEXT("Signed route width has failed native lane samples; inspect routeWidthSamples"));
            RouteFailures.Add(MakeShared<FJsonValueObject>(Failure)); bWidthPassed=false;
        }
        ++WidthRouteIndex; bWidthComplete=WidthRouteIndex==Routes.Num();
        UE_LOG(LogTemp,Display,TEXT("WAR_CITADEL_WIDTH %s passed=%d routes=%d/%d samples=%d"),
            *WidthRoute->GetStringField(TEXT("id")),RoutePassed,WidthRouteIndex,Routes.Num(),RouteWidthSamples.Num());
        if (bWidthComplete)
        {
            auto Diagnostic=MakeShared<FJsonObject>();
            Diagnostic->SetBoolField(TEXT("diagnosticOnly"),true);Diagnostic->SetBoolField(TEXT("passed"),false);
            Diagnostic->SetStringField(TEXT("signature"),Signature);Diagnostic->SetStringField(TEXT("map"),GetWorld()->GetOutermost()->GetName());
            Diagnostic->SetStringField(TEXT("mapSha256"),MapSha256);Diagnostic->SetStringField(TEXT("cityRevision"),CityRevision);
            Diagnostic->SetBoolField(TEXT("routeWidthComplete"),true);Diagnostic->SetBoolField(TEXT("routeWidthPassed"),bWidthPassed);
            Diagnostic->SetObjectField(TEXT("routeWidthConfig"),RouteWidthConfig);
            Diagnostic->SetArrayField(TEXT("routeWidthSamples"),RouteWidthSamples);
            Diagnostic->SetArrayField(TEXT("physicalFailures"),PhysicalFailures);
            Diagnostic->SetNumberField(TEXT("capsuleRadiusCm"),Radius);Diagnostic->SetNumberField(TEXT("capsuleHeightCm"),Half*2);
            Diagnostic->SetBoolField(TEXT("visualApproved"),false);Diagnostic->SetBoolField(TEXT("citywideAcceptance"),false);
            Diagnostic->SetBoolField(TEXT("releaseAcceptance"),false);
            if (!WarCitadelProofJson::Save(Diagnostic,Directory/TEXT("width-diagnostic.json")))
            { Finish(false,TEXT("Cannot save complete provisional route-width diagnostics"));return; }
            if (FParse::Param(FCommandLine::Get(),TEXT("WarCitadelWidthDiagnostic")))
                Finish(false,TEXT("Diagnostic-only native corridor samples completed; no traversal or visual acceptance"));
        }
        return;
    }
    if (ViewIndex<Views.Num())
    {
        HideArchitectureUi();
        auto View=Views[ViewIndex]->AsObject();
        if (!bPositioned)
        {
            const FVector Eye=Point(View->GetArrayField(TEXT("eye"))),Target=Point(View->GetArrayField(TEXT("target")));
            if (!Camera.IsValid()) Camera=GetWorld()->SpawnActor<ACameraActor>();
            double FieldOfView=68,OrthoWidth=0;
            View->TryGetNumberField(TEXT("fieldOfView"),FieldOfView);
            View->TryGetNumberField(TEXT("orthographicWidthCm"),OrthoWidth);
            if (Eye.ContainsNaN() || Target.ContainsNaN() || (Target-Eye).IsNearlyZero()
                || !FMath::IsFinite(FieldOfView) || FieldOfView<10 || FieldOfView>120
                || !FMath::IsFinite(OrthoWidth) || OrthoWidth<0 || OrthoWidth>100000)
            { Finish(false,TEXT("Invalid reference-aligned camera"));return; }
            Camera->SetActorLocationAndRotation(Eye,(Target-Eye).Rotation());
            Camera->GetCameraComponent()->SetFieldOfView(FieldOfView);
            Camera->GetCameraComponent()->SetProjectionMode(OrthoWidth>0 ? ECameraProjectionMode::Orthographic : ECameraProjectionMode::Perspective);
            if (OrthoWidth>0) Camera->GetCameraComponent()->SetOrthoWidth(OrthoWidth);
            PC->bAutoManageActiveCameraTarget=false;PC->SetViewTarget(Camera.Get());
            Next=Now+ViewSettleSeconds;bPositioned=true;bCaptured=false;return;
        }
        if (Now>Next-3 && DeltaTime>0)
        {
            Frames.Add(DeltaTime*1000);
            ViewFrames.Add(DeltaTime*1000);ViewDrawCalls.Add(GNumDrawCallsRHI[0]);
            DrawCalls.Add(GNumDrawCallsRHI[0]);Primitives.Add(GNumPrimitivesDrawnRHI[0]);
            PeakStreamingRequests=FMath::Max(PeakStreamingRequests,IStreamingManager::Get().GetNumWantingResources());
        }
        if (Now<Next) return;
        if (!bCaptured)
        {
            FScreenshotRequest::RequestScreenshot(Directory/FString::Printf(TEXT("view_%02d.png"),ViewIndex),false,false);
            bCaptured=true;Next=Now+1;return;
        }
        ViewFrames.Sort();ViewDrawCalls.Sort();
        auto Metric=MakeShared<FJsonObject>();Metric->SetStringField(TEXT("id"),View->GetStringField(TEXT("id")));
        bool HudHidden=true,WidgetsCollapsed=true;
        for (const auto& Pair:SavedHudVisibility) if (const auto* Hud=Pair.Key.Get()) HudHidden&=!Hud->bShowHUD;
        for (const auto& Pair:SavedWidgetVisibility) if (const auto* Widget=Pair.Key.Get();Widget && Widget->IsInViewport())
            WidgetsCollapsed&=Widget->GetVisibility()==ESlateVisibility::Collapsed;
        Metric->SetBoolField(TEXT("canvasHudHidden"),HudHidden);
        Metric->SetBoolField(TEXT("viewportWidgetsCollapsed"),WidgetsCollapsed);
        Metric->SetNumberField(TEXT("canvasHudCount"),SavedHudVisibility.Num());
        Metric->SetNumberField(TEXT("viewportWidgetCount"),SavedWidgetVisibility.Num());
        const FVector ActualEye=Camera->GetActorLocation(),ActualDirection=Camera->GetActorForwardVector();
        const auto JsonVector=[](const FVector& Value)
        { return TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(Value.X),MakeShared<FJsonValueNumber>(Value.Y),MakeShared<FJsonValueNumber>(Value.Z)}; };
        Metric->SetArrayField(TEXT("eye"),JsonVector(ActualEye));Metric->SetArrayField(TEXT("direction"),JsonVector(ActualDirection));
        Metric->SetNumberField(TEXT("fieldOfView"),Camera->GetCameraComponent()->FieldOfView);
        const bool Orthographic=Camera->GetCameraComponent()->ProjectionMode==ECameraProjectionMode::Orthographic;
        Metric->SetStringField(TEXT("projection"),Orthographic ? TEXT("orthographic") : TEXT("perspective"));
        if (Orthographic) Metric->SetNumberField(TEXT("orthographicWidthCm"),Camera->GetCameraComponent()->OrthoWidth);
        if (!ViewFrames.IsEmpty()) Metric->SetNumberField(TEXT("p95FrameMs"),ViewFrames[FMath::Min(ViewFrames.Num()-1,FMath::FloorToInt(ViewFrames.Num()*.95))]);
        if (!ViewDrawCalls.IsEmpty()) Metric->SetNumberField(TEXT("p95DrawCalls"),ViewDrawCalls[FMath::Min(ViewDrawCalls.Num()-1,FMath::FloorToInt(ViewDrawCalls.Num()*.95))]);
        Metric->SetNumberField(TEXT("physicalMiB"),FPlatformMemory::GetStats().UsedPhysical/1048576.0);
        ViewPerformance.Add(MakeShared<FJsonValueObject>(Metric));ViewFrames.Reset();ViewDrawCalls.Reset();
        UE_LOG(LogTemp,Display,TEXT("WAR_DUTCH_VIEW=%d/%d"),ViewIndex+1,Views.Num());
        ++ViewIndex;bPositioned=false;return;
    }
    RestoreArchitectureUi();
    if (RouteIndex>=Routes.Num()) { Finish(RouteFailures.IsEmpty(),TEXT("Saved lighting views and configured capsule routes completed; inspect routeFailures"));return; }
    auto Route=Routes[RouteIndex]->AsObject();const auto Points=Route->GetArrayField(TEXT("points"));
    if (Points.Num()<2) { Finish(false,TEXT("Missing traversal route"));return; }
    if (!bPositioned)
    {
        Pawn->SetActorLocation(Point(Points[0]->AsArray())+FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3),false);
        Pawn->GetCharacterMovement()->StopMovementImmediately();Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        PreviousFeet=Point(Points[0]->AsArray());RouteDistance=0;
        RouteStarted=Now;LastProgress=Now;BestDistance=MAX_dbl;Waypoint=1;Next=Now+.5;bPositioned=true;return;
    }
    if (Now<Next) return;
    FVector Feet=Pawn->GetActorLocation()-FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    RouteDistance+=FVector::Dist2D(Feet,PreviousFeet);PreviousFeet=Feet;
    const FVector Target=Point(Points[Waypoint]->AsArray());
    double Width=0;
    if (Route->TryGetNumberField(TEXT("clearWidthCm"),Width))
    {
        const FVector From=Point(Points[Waypoint-1]->AsArray());
        const FVector Segment=Target-From;
        const double Alpha=FMath::Clamp(FVector::DotProduct((Feet-From).GetSafeNormal2D(),Segment.GetSafeNormal2D())
            *FVector::Dist2D(Feet,From)/FMath::Max(1.0,Segment.Size2D()),0.0,1.0);
        const FVector Corridor=From+Segment*Alpha;
        if (Pawn->GetCapsuleComponent()->GetCollisionEnabled()==ECollisionEnabled::NoCollision
            || !Pawn->GetActorEnableCollision() || !Pawn->IsVisualReady()
            || FVector::Dist2D(Feet,Corridor)>FMath::Max(0.0,Width*.5-Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius())
            || FMath::Abs(Feet.Z-Corridor.Z)>120)
        {
            auto Failure=MakeShared<FJsonObject>();
            Failure->SetStringField(TEXT("id"),Route->GetStringField(TEXT("id")));
            Failure->SetStringField(TEXT("reason"),TEXT("Character left the intended physical corridor or lost visual/collision readiness"));
            Failure->SetStringField(TEXT("feet"),Feet.ToString());
            RouteFailures.Add(MakeShared<FJsonValueObject>(Failure));
            Pawn->GetCharacterMovement()->StopMovementImmediately();++RouteIndex;bPositioned=false;return;
        }
    }
    const double Distance=FVector::Dist2D(Feet,Target);
    if (Distance<BestDistance-5) { BestDistance=Distance;LastProgress=Now; }
    if (Now-RouteStarted>75 || Now-LastProgress>10)
    {
        auto Failure=MakeShared<FJsonObject>();
        Failure->SetStringField(TEXT("id"),Route->GetStringField(TEXT("id")));
        Failure->SetNumberField(TEXT("waypoint"),Waypoint);
        Failure->SetStringField(TEXT("feet"),Feet.ToString());Failure->SetStringField(TEXT("target"),Target.ToString());
        RouteFailures.Add(MakeShared<FJsonValueObject>(Failure));
        UE_LOG(LogTemp,Warning,TEXT("WAR_DUTCH_ROUTE_BLOCKED=%s feet=%s target=%s"),*Route->GetStringField(TEXT("id")),*Feet.ToString(),*Target.ToString());
        Pawn->GetCharacterMovement()->StopMovementImmediately();++RouteIndex;bPositioned=false;return;
    }
    if (FVector::Dist2D(Feet,Target)<30 && FMath::Abs(Feet.Z-Target.Z)<45)
    {
        BestDistance=MAX_dbl;LastProgress=Now;
        if (++Waypoint>=Points.Num())
        {
            auto Completed=MakeShared<FJsonObject>();
            Completed->SetStringField(TEXT("id"),Route->GetStringField(TEXT("id")));
            Completed->SetNumberField(TEXT("waypoints"),Points.Num());
            Completed->SetNumberField(TEXT("seconds"),Now-RouteStarted);
            Completed->SetNumberField(TEXT("distanceCm"),RouteDistance);
            Completed->SetBoolField(TEXT("grounded"),Pawn->GetCharacterMovement()->IsMovingOnGround());
            Completed->SetBoolField(TEXT("collisionEnabled"),Pawn->GetActorEnableCollision()
                && Pawn->GetCapsuleComponent()->GetCollisionEnabled()!=ECollisionEnabled::NoCollision);
            CompletedRoutes.Add(MakeShared<FJsonValueObject>(Completed));
            UE_LOG(LogTemp,Display,TEXT("WAR_DUTCH_ROUTE=%s %d/%d"),*Route->GetStringField(TEXT("id")),RouteIndex+1,Routes.Num());
            Pawn->GetCharacterMovement()->StopMovementImmediately();++RouteIndex;bPositioned=false;
        }
        return;
    }
    Pawn->AddMovementInput((Target-Feet).GetSafeNormal2D(),1.0f,true);
}
